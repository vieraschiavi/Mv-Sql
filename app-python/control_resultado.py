# © 2026 Martín Viera. Todos los derechos reservados.

"""
control_resultado.py — MV SQL NLP
==================================================================
Pestaña «Control»: ¿el resultado que estoy viendo es confiable?

La validación del motor (motor.validar_sql) garantiza dos cosas: que la
consulta es de solo lectura y que no inventó tablas. NO garantiza que
el número sea el correcto. Los dos errores que más se ven en consultas
de varias tablas pasan en verde y no tiran ningún error:

  1. Un JOIN contra una tabla cuya clave está REPETIDA multiplica las
     filas: los totales salen inflados y nadie se entera.
  2. Un INNER JOIN contra una tabla a la que le faltan claves descarta
     filas en silencio: los totales salen cortos.

Y aparte, las columnas mismas pueden venir mal: vacías, con fechas
centinela (1900-01-01, 9999-12-31), con números guardados como texto
o con espacios que rompen cualquier cruce posterior.

Acá hay dos controles:

  * perfil_columnas(df): una fila por columna del resultado — nulos,
    distintos, mínimo, máximo, suma — y las alertas de cada una. Corre
    sobre el DataFrame que ya está en memoria: no consulta la base.

  * verificar_joins(cx, sql, catalogo): lee los JOIN ... ON del SQL y,
    para cada uno, pregunta a la base (solo lectura, dos consultas
    agregadas por join) si la clave de la tabla que se une es única y
    cuántas filas de la otra tabla no tienen pareja. Con eso clasifica
    el join en N:1 (bien), 1:N (ojo al sumar) o N:N (duplica filas).

Las alertas se devuelven como CÓDIGOS, no como texto: la pantalla las
traduce (ES/EN/PT). Este módulo no importa Streamlit, así que se prueba
solo.
==================================================================
"""

import re
from datetime import date, datetime

import pandas as pd

from conectores import _sin_comentarios, _sin_literales

# ──────────────────────────────────────────────────────────────
# 1) Perfil de columnas
# ──────────────────────────────────────────────────────────────

#: % de nulos a partir del cual una columna se marca para revisar.
UMBRAL_NULOS = 20.0

#: Años que en la práctica son «no hay fecha» cargado a mano o por
#: default del sistema de origen (1900-01-01, 1753-01-01, 9999-12-31).
ANIO_CENTINELA_MIN = 1900
ANIO_CENTINELA_MAX = 9999

#: Fracción de valores que tienen que poder leerse como número para que
#: una columna de texto se considere «números guardados como texto».
UMBRAL_TEXTO_NUMERICO = 0.9

#: Severidad de cada alerta. «revisar» cambia el semáforo; «info» no.
SEVERIDAD = {
    "vacia": "revisar",
    "nulos_altos": "revisar",
    "fecha_centinela": "revisar",
    "constante": "info",
    "negativos": "info",
    "texto_numerico": "info",
    "espacios": "info",
}

_PARECE_FECHA = re.compile(r"fecha|date|data|periodo|period|dia\b|mes\b", re.IGNORECASE)


def _como_numero(serie):
    """La serie como números, o None si no lo es.

    SQL Server y PostgreSQL devuelven DECIMAL/MONEY como `decimal.Decimal`,
    y pandas deja esa columna como `object`: sin esto, el importe no
    tendría suma ni mínimo en el control.
    """
    if pd.api.types.is_bool_dtype(serie) or _es_booleana(serie):
        return None
    if pd.api.types.is_numeric_dtype(serie):
        return serie
    no_nulos = serie.dropna()
    if no_nulos.empty:
        return None
    # Solo valores que YA son números (Decimal, int, float): un texto
    # «123» no es un número, es un número guardado como texto (otra alerta).
    if all(isinstance(v, (int, float)) or type(v).__name__ == "Decimal"
           for v in no_nulos.head(200)):
        convertida = pd.to_numeric(serie, errors="coerce")
        if convertida.notna().sum() == len(no_nulos):
            return convertida
    return None


def _es_booleana(serie):
    """Un `bit` de SQL Server con NULL llega como True/False/None en una
    columna object; como `isinstance(True, int)` es verdadero, sin esto
    salía «número» con suma."""
    no_nulos = serie.dropna()
    return (not no_nulos.empty and serie.dtype == object
            and all(isinstance(v, bool) for v in no_nulos.head(200)))


_ISO = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})")
_DMY = re.compile(r"^\s*\d{1,2}/\d{1,2}/(\d{4})")


def _anio(v):
    """Año de una fecha (objeto o texto), o None si no parece una fecha.

    No pasa por pandas a propósito: `9999-12-31` —la fecha centinela más
    común— queda fuera del rango de pandas y se volvería NaT justo cuando
    hay que detectarla.
    """
    if isinstance(v, (datetime, date)):
        return v.year
    if isinstance(v, str):
        m = _ISO.match(v)
        if m:
            _a, mes, dia = (int(x) for x in m.groups())
            return int(m.group(1)) if 1 <= mes <= 12 and 1 <= dia <= 31 else None
        m = _DMY.match(v)
        return int(m.group(1)) if m else None
    return None


def _fechas(serie, nombre):
    """(anios, minimo, maximo) si la columna es de fechas, o None."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        validas = serie.dropna()
        if validas.empty:
            return [], None, None
        return (list(validas.dt.year), _valor_legible(validas.min()),
                _valor_legible(validas.max()))
    # pandas 3 guarda el texto como dtype «str», no «object»: mirar solo
    # object dejaba todas las fechas-texto (SQLite, CSV) sin detectar.
    if not (serie.dtype == object or pd.api.types.is_string_dtype(serie)):
        return None
    no_nulos = serie.dropna()
    if no_nulos.empty:
        return None
    son_objetos = all(isinstance(v, (datetime, date)) for v in no_nulos.head(200))
    if not son_objetos and not _PARECE_FECHA.search(str(nombre)):
        return None
    anios = [_anio(v) for v in no_nulos]
    if sum(a is not None for a in anios) < 0.9 * len(no_nulos):
        return None
    fechas = [v for v, a in zip(no_nulos, anios) if a is not None]
    # Una sola clave de orden para todo: `min()` directo sobre date y
    # datetime mezclados tira TypeError (no se comparan entre sí).
    mn = min(fechas, key=_clave_dmy)
    mx = max(fechas, key=_clave_dmy)
    return [a for a in anios if a is not None], _valor_legible(mn), _valor_legible(mx)


def _clave_dmy(v):
    """(año, mes, día, hora, minuto, segundo) de una fecha objeto o texto.

    Texto con barras: día/mes/año (el formato de la región), salvo que el
    segundo número pase de 12 — entonces es mes/día/año (12/31/2024).
    """
    if isinstance(v, datetime):
        return (v.year, v.month, v.day, v.hour, v.minute, v.second)
    if isinstance(v, date):
        return (v.year, v.month, v.day, 0, 0, 0)
    m = _ISO.match(v)
    if m:
        return tuple(int(x) for x in m.groups()) + (0, 0, 0)
    a, b, y = (int(x) for x in re.findall(r"\d+", v)[:3])
    dia, mes = (b, a) if b > 12 else (a, b)
    return (y, mes, dia, 0, 0, 0)


def _texto_numerico(serie):
    no_nulos = serie.dropna()
    if no_nulos.empty or not all(isinstance(v, str) for v in no_nulos.head(200)):
        return False
    limpios = no_nulos.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(limpios, errors="coerce").notna().mean() >= UMBRAL_TEXTO_NUMERICO


def _valor_legible(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime("%Y-%m-%d %H:%M:%S").replace(" 00:00:00", "")
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "item"):          # numpy → escalar de Python
        return v.item()
    return v


def perfil_columnas(df):
    """Una fila (dict) por columna del resultado.

    Claves: columna, tipo (numero/fecha/texto/booleano), filas, nulos,
    pct_nulos, distintos, minimo, maximo, suma, negativos, frecuente,
    alertas (lista de códigos de SEVERIDAD).
    """
    perfil = []
    filas = len(df)
    for i, nombre in enumerate(df.columns):
        # Por POSICIÓN: con «SELECT v.id, c.id» hay dos columnas «id», y
        # df["id"] devolvía siempre la primera.
        serie = df.iloc[:, i]
        nulos = int(serie.isna().sum())
        try:
            distintos = int(serie.nunique(dropna=True))
        except TypeError:                        # valores no hasheables
            distintos = int(serie.astype(str).nunique(dropna=True))
        fila = {
            "columna": str(nombre), "tipo": "texto", "filas": filas, "nulos": nulos,
            "pct_nulos": round(100.0 * nulos / filas, 1) if filas else None,
            "distintos": distintos, "minimo": None, "maximo": None, "suma": None,
            "negativos": None, "frecuente": None, "alertas": [],
        }
        alertas = fila["alertas"]

        numero = _como_numero(serie)
        fecha = None if numero is not None else _fechas(serie, nombre)
        if pd.api.types.is_bool_dtype(serie) or _es_booleana(serie):
            fila["tipo"] = "booleano"
        elif numero is not None:
            fila["tipo"] = "numero"
            if numero.notna().any():
                fila["minimo"] = _valor_legible(numero.min())
                fila["maximo"] = _valor_legible(numero.max())
                fila["suma"] = _valor_legible(numero.sum())
                fila["negativos"] = int((numero < 0).sum())
                if fila["negativos"]:
                    alertas.append("negativos")
        elif fecha is not None:
            fila["tipo"] = "fecha"
            anios, fila["minimo"], fila["maximo"] = fecha
            if any(a <= ANIO_CENTINELA_MIN or a >= ANIO_CENTINELA_MAX for a in anios):
                alertas.append("fecha_centinela")
        else:
            no_nulos = serie.dropna()
            if not no_nulos.empty:
                try:
                    top = no_nulos.value_counts().head(1)
                    fila["frecuente"] = f"{top.index[0]} ({int(top.iloc[0])})"
                except TypeError:
                    fila["frecuente"] = None
                if _texto_numerico(serie):
                    alertas.append("texto_numerico")
                textos = no_nulos[no_nulos.map(lambda v: isinstance(v, str))]
                if not textos.empty and (textos != textos.str.strip()).any():
                    alertas.append("espacios")

        if filas and nulos == filas:
            alertas.insert(0, "vacia")
        elif fila["pct_nulos"] is not None and fila["pct_nulos"] >= UMBRAL_NULOS:
            alertas.insert(0, "nulos_altos")
        if filas > 1 and distintos == 1 and nulos == 0:
            alertas.append("constante")
        perfil.append(fila)
    return perfil


def filas_duplicadas(df):
    """Cuántas filas son copia exacta de otra anterior (0 si no hay)."""
    if df.empty:
        return 0
    try:
        return int(df.duplicated().sum())
    except TypeError:                            # celdas no hasheables
        return int(df.astype(str).duplicated().sum())


# ──────────────────────────────────────────────────────────────
# 2) Lectura de los JOIN del SQL
# ──────────────────────────────────────────────────────────────
#
# Regla de oro: un join que no se entiende del todo NO se verifica. Un ON
# con una condición de vigencia (BETWEEN, = 1), un OR, una función sobre
# la clave o una subconsulta cambian qué filas se cruzan; verificar solo
# la igualdad de claves daría un «duplica filas» falso sobre una consulta
# correcta. Esos joins se devuelven con `verificable=False` y el motivo.

_ID = r'(?:\[[^\]]+\]|"[^"]+"|`[^`]+`|[A-Za-z_][\w$]*)'
_QUAL = rf"{_ID}(?:\s*\.\s*{_ID}){{0,2}}"

#: Palabras que pueden seguir a un nombre de tabla y NO son un alias.
_NO_ALIAS = {
    "where", "join", "inner", "left", "right", "full", "cross", "outer", "on",
    "group", "order", "having", "limit", "offset", "union", "except", "intersect",
    "with", "natural", "using", "fetch", "window", "qualify", "as", "hash", "loop",
    "merge", "remote", "apply", "pivot", "unpivot", "tablesample",
}
_NO_ALIAS_RX = "|".join(sorted(_NO_ALIAS))
# El alias no puede ser una palabra clave: sin el lookahead, en «FROM ventas
# JOIN precios» el regex se comía el JOIN como alias y ese join no existía.
_REF_TABLA = re.compile(
    rf"\b(?P<kw>from|join)\s+(?P<tabla>{_QUAL})"
    rf"(?:\s+(?:as\s+)?(?!(?:{_NO_ALIAS_RX})\b)(?P<alias>{_ID}))?",
    re.IGNORECASE)
_JOIN = re.compile(r"\bjoin\b", re.IGNORECASE)
# Tipo del join, con los hints de SQL Server (LEFT HASH JOIN, INNER LOOP JOIN).
_TIPO_JOIN = re.compile(
    r"\b(left|right|full|cross|inner|natural)?\s*(?:outer\s+)?"
    r"(?:(?:hash|loop|merge|remote)\s+)?join\s*$", re.IGNORECASE)
# Dónde termina una condición ON. «LEFT(» es una función, no un join: por
# eso LEFT/RIGHT solo cortan si les sigue JOIN.
_FIN_ON = re.compile(
    r"\b(?:(?:inner|left|right|full|cross|natural)(?:\s+outer)?"
    r"(?:\s+(?:hash|loop|merge|remote))?\s+join|join|where|group\s+by|order\s+by|"
    r"having|union|limit|except|intersect|window|qualify|fetch|offset)\b", re.IGNORECASE)
_IGUAL_COLS = re.compile(rf"^\s*(?P<a>{_QUAL})\s*=\s*(?P<b>{_QUAL})\s*$")
_CTE = re.compile(rf"(?:\bwith\b|,)\s*(?P<n>{_ID})\s*(?:\([^)]*\))?\s+as\s*\(", re.IGNORECASE)
_COMA = re.compile(
    rf"\bfrom\s+{_QUAL}(?:\s+(?:as\s+)?(?!(?:{_NO_ALIAS_RX})\b){_ID})?"
    rf"(?:\s+with\s*\([^)]*\))?\s*,", re.IGNORECASE)


def _limpio(identificador):
    return identificador.strip().strip('[]"`')


def _crudas(calificado):
    """Las partes de un nombre calificado TAL COMO se escribieron (con comillas)."""
    return re.findall(_ID, calificado)


def _partes(calificado):
    return [_limpio(p) for p in _crudas(calificado)]


def _grupos(texto):
    """grupo[i]: posición del paréntesis abierto más interno que contiene i (-1 = afuera).

    Los alias valen dentro de su SELECT: `v` en una subconsulta no es la `v`
    de afuera. Sin esto, «... WHERE v.x IN (SELECT v.x FROM devoluciones v)»
    resolvía el join de afuera contra `devoluciones`.
    """
    grupo, pila = [], []
    for i, ch in enumerate(texto):
        if ch == ")" and pila:
            pila.pop()
        grupo.append(pila[-1] if pila else -1)
        if ch == "(":
            pila.append(i)
    return grupo


def _sin_parentesis_externos(cond):
    cond = cond.strip()
    while cond.startswith("(") and cond.endswith(")"):
        nivel = 0
        for i, ch in enumerate(cond):
            nivel += ch == "("
            nivel -= ch == ")"
            if nivel == 0 and i < len(cond) - 1:
                return cond            # «(a) AND (b)»: los de afuera no envuelven todo
        cond = cond[1:-1].strip()
    return cond


def _terminos_and(cond):
    """Los términos de un AND de primer nivel, o None si hay un OR."""
    cond = _sin_parentesis_externos(cond)
    terminos, nivel, ini = [], 0, 0
    for m in re.finditer(r"\(|\)|\band\b|\bor\b", cond, re.IGNORECASE):
        tok = m.group(0).lower()
        if tok == "(":
            nivel += 1
        elif tok == ")":
            nivel -= 1
        elif nivel == 0 and tok == "or":
            return None
        elif nivel == 0 and tok == "and":
            terminos.append(cond[ini:m.start()])
            ini = m.end()
    terminos.append(cond[ini:])
    return [_sin_parentesis_externos(t) for t in terminos]


def _no_leido(tipo, unida="", motivo="no_leido"):
    return {"tipo": tipo, "base": "", "col_base": [], "unida": unida, "col_unida": [],
            "verificable": False, "motivo": motivo}


def _condicion_on(texto, desde, hasta):
    """El texto del ON entre `desde` y `hasta`, o None si no hay ON."""
    tramo = texto[desde:hasta]
    on = re.search(r"\bon\b", tramo, re.IGNORECASE)
    if not on or re.match(r"\s*using\b", tramo, re.IGNORECASE):
        return None
    # Se corta con el texto que SIGUE (no con `tramo`): el próximo join
    # empieza en su «JOIN», así que el «INNER »/«LEFT » que lo precede
    # quedaría pegado al final de esta condición.
    cond = texto[desde + on.end():]
    fin = _FIN_ON.search(cond)
    if fin:
        cond = cond[:fin.start()]
    nivel = 0                     # un «)» de más cierra la subconsulta que contiene al join
    for i, ch in enumerate(cond):
        nivel += ch == "("
        nivel -= ch == ")"
        if nivel < 0:
            return cond[:i]
    return cond


def joins_del_sql(sql):
    """Los JOIN del SQL.

    Devuelve una lista de dicts: tipo (INNER/LEFT/RIGHT/FULL), la tabla
    ya existente (`base`, `col_base`) y la que se une (`unida`,
    `col_unida`), escritas TAL CUAL en el SQL (con esquema y comillas, si
    las llevan: `"ClienteId"` en PostgreSQL no es `ClienteId`). Las claves
    compuestas (ON a.x = b.x AND a.y = b.y) quedan en un solo join.

    Los joins que no se pueden verificar se devuelven igual, con
    `verificable=False` y `motivo`: «cte» (une un CTE o una subconsulta),
    «on_complejo» (el ON no es solo igualdades entre columnas) o
    «no_leido» (USING, NATURAL, JOIN a una subconsulta, FROM a, b).
    """
    texto = _sin_literales(_sin_comentarios(sql or ""))
    ctes = {_limpio(m.group("n")).lower() for m in _CTE.finditer(texto)}
    grupo = _grupos(texto)

    refs = []                            # (pos, fin, palabra, tabla, alias, grupo)
    alias_por_grupo = {}
    for m in _REF_TABLA.finditer(texto):
        tabla = re.sub(r"\s*\.\s*", ".", m.group("tabla").strip())
        alias = m.group("alias")
        g = grupo[m.start()]
        refs.append((m.start(), m.end(), m.group("kw").lower(), tabla, alias, g))
        nombres = alias_por_grupo.setdefault(g, {})
        nombres.setdefault(_partes(tabla)[-1].lower(), tabla)
        if alias:
            nombres[_limpio(alias).lower()] = tabla

    joins = []
    en_ref = {pos for pos, _f, kw, *_ in refs if kw == "join"}
    for m in _JOIN.finditer(texto):
        if m.start() in en_ref:
            continue
        tm = _TIPO_JOIN.search(texto[max(0, m.start() - 40):m.end()])
        if tm and (tm.group(1) or "").lower() == "cross":
            continue
        joins.append(_no_leido("JOIN"))          # JOIN (SELECT ...) x, JOIN LATERAL, ...

    for m in _COMA.finditer(texto):
        joins.append(_no_leido(",", unida=""))

    for pos, fin_ref, kw, tabla, alias, g in refs:
        if kw != "join":
            continue
        tm = _TIPO_JOIN.search(texto[max(0, pos - 40):pos + 4])
        tipo = ((tm.group(1) or "inner") if tm else "inner").upper()
        if tipo == "CROSS":
            continue
        if tipo == "NATURAL":
            joins.append(_no_leido(tipo, tabla))
            continue
        siguiente = min([p for p, *_ in refs if p > pos] or [len(texto)])
        cond = _condicion_on(texto, fin_ref, siguiente)
        if cond is None:
            joins.append(_no_leido(tipo, tabla))
            continue
        # Con alias, la tabla se nombra SOLO por el alias (y así un self-join
        # «FROM emp JOIN emp m ON m.id = emp.jefe» distingue los dos lados).
        propio = _limpio(alias).lower() if alias else _partes(tabla)[-1].lower()
        terminos = _terminos_and(cond)
        pares, otros = [], set()
        for termino in terminos or [""]:
            ig = _IGUAL_COLS.match(termino)
            if not ig:
                pares = None
                break
            a, b = _crudas(ig.group("a")), _crudas(ig.group("b"))
            if len(a) < 2 or len(b) < 2:
                pares = None
                break
            lado_a, lado_b = _limpio(a[-2]).lower(), _limpio(b[-2]).lower()
            if lado_b == propio and lado_a != propio:
                otros.add(lado_a)
                pares.append((a[-1], b[-1]))
            elif lado_a == propio and lado_b != propio:
                otros.add(lado_b)
                pares.append((b[-1], a[-1]))
            else:
                pares = None
                break
        if not pares or len(otros) != 1:
            joins.append(_no_leido(tipo, tabla, "on_complejo"))
            continue
        otro = otros.pop()
        base = alias_por_grupo.get(g, {}).get(otro)
        es_cte = (base is None or _partes(base)[-1].lower() in ctes
                  or _partes(tabla)[-1].lower() in ctes)
        joins.append({
            "tipo": tipo, "base": base or otro, "col_base": [p[0] for p in pares],
            "unida": tabla, "col_unida": [p[1] for p in pares],
            "verificable": not es_cte, "motivo": "cte" if es_cte else None,
        })
    return joins


# ──────────────────────────────────────────────────────────────
# 3) Verificación de los joins contra la base
# ──────────────────────────────────────────────────────────────

_SEGURO = re.compile(rf"^{_QUAL}$")
_SEGURO_COL = re.compile(rf"^{_ID}$")


def _columnas_catalogo(catalogo, tabla):
    info = catalogo.get("tablas", {}).get(_partes(tabla)[-1])
    if info is None:        # el catálogo puede guardar el nombre con otra caja
        buscado = _partes(tabla)[-1].lower()
        for nombre, datos in catalogo.get("tablas", {}).items():
            if nombre.lower() == buscado:
                info = datos
                break
    if info is None:
        return None
    return {c["columna"].lower(): c for c in info.get("columnas", [])}


def _cita(col, dialecto):
    """La columna lista para el SQL.

    Si ya viene citada (`"ClienteId"`, `[Cliente ID]`) se usa TAL CUAL: es
    como la escribió la consulta que ya corrió bien. Sacarle las comillas en
    PostgreSQL la pasaba a minúsculas y la verificación fallaba.
    """
    if col[:1] in '["`' or re.fullmatch(r"[A-Za-z_][\w]*", col):
        return col
    d = (dialecto or "").lower()
    if "sql server" in d:
        return "[" + col.replace("]", "]]") + "]"
    if "mysql" in d:
        return "`" + col.replace("`", "``") + "`"
    return '"' + col.replace('"', '""') + '"'


def sql_claves_repetidas(tabla, columnas, dialecto=""):
    """Cuántos valores de clave aparecen más de una vez en `tabla`."""
    cols = ", ".join(_cita(c, dialecto) for c in columnas)
    no_nulos = " AND ".join(f"{_cita(c, dialecto)} IS NOT NULL" for c in columnas)
    return (f"SELECT COUNT(*) AS claves_repetidas FROM ("
            f"SELECT {cols} FROM {tabla} WHERE {no_nulos} "
            f"GROUP BY {cols} HAVING COUNT(*) > 1) repetidas")


def sql_huerfanas(base, col_base, unida, col_unida, dialecto=""):
    """Filas de `base` con clave cargada que no tienen pareja en `unida`."""
    cond = " AND ".join(f"u_.{_cita(cu, dialecto)} = b_.{_cita(cb, dialecto)}"
                        for cb, cu in zip(col_base, col_unida))
    no_nulos = " AND ".join(f"b_.{_cita(c, dialecto)} IS NOT NULL" for c in col_base)
    return (f"SELECT COUNT(*) AS huerfanas FROM {base} b_ WHERE {no_nulos} "
            f"AND NOT EXISTS (SELECT 1 FROM {unida} u_ WHERE {cond})")


def _es_pk(tabla, cols_catalogo, columnas):
    """La clave es la PK completa de la tabla (entonces es única sin preguntar).

    Solo para un nombre sin esquema: el catálogo se indexa por nombre
    simple, y `otro_esquema.clientes` no tiene por qué compartir la PK de
    `clientes`. Con esquema, se pregunta a la base.
    """
    if "." in tabla:
        return False
    pks = {n for n, c in cols_catalogo.items() if c.get("pk")}
    return bool(pks) and pks == {_limpio(c).lower() for c in columnas}


def clasificar(base_unica, unida_unica):
    """Cardinalidad del join, vista desde la tabla que se une."""
    if unida_unica:
        return "1:1" if base_unica else "N:1"
    return "1:N" if base_unica else "N:N"


def verificar_joins(cx, sql, catalogo, ejecutar=None):
    """Chequea cada JOIN del SQL contra la base (solo lectura).

    `ejecutar(sql) -> (columnas, filas, sql_ejecutado)` permite inyectar
    el ejecutor; por defecto usa `cx.ejecutar` sin tope (son agregados:
    devuelven una fila).

    Devuelve una lista de dicts: la info de joins_del_sql más
    `repetidas_base`, `repetidas_unida`, `huerfanas`, `relacion`
    (1:1/N:1/1:N/N:N), `estado` (ok/revisar/error/no_verificable) y
    `motivo` (código para traducir), o `error` con el mensaje del motor.
    """
    dialecto = getattr(cx, "dialecto", "")
    correr = ejecutar or (lambda q: cx.ejecutar(q, limite=None))

    def uno(q):
        _cols, filas, _ = correr(q)
        return int(filas[0][0] or 0) if filas else 0

    salida = []
    for j in joins_del_sql(sql):
        fila = dict(j, repetidas_base=None, repetidas_unida=None, huerfanas=None,
                    relacion=None, estado="no_verificable",
                    motivo=j.get("motivo") or "cte", error=None)
        salida.append(fila)
        if not j["verificable"]:
            continue
        cat_b = _columnas_catalogo(catalogo, j["base"])
        cat_u = _columnas_catalogo(catalogo, j["unida"])
        cols = j["col_base"] + j["col_unida"]
        if (cat_b is None or cat_u is None
                or not _SEGURO.match(j["base"]) or not _SEGURO.match(j["unida"])
                or not all(_SEGURO_COL.match(c) for c in cols)
                or any(_limpio(c).lower() not in cat_b for c in j["col_base"])
                or any(_limpio(c).lower() not in cat_u for c in j["col_unida"])):
            fila["motivo"] = "fuera_catalogo"
            continue
        try:
            fila["repetidas_unida"] = (
                0 if _es_pk(j["unida"], cat_u, j["col_unida"]) else
                uno(sql_claves_repetidas(j["unida"], j["col_unida"], dialecto)))
            fila["repetidas_base"] = (
                0 if _es_pk(j["base"], cat_b, j["col_base"]) else
                uno(sql_claves_repetidas(j["base"], j["col_base"], dialecto)))
            fila["huerfanas"] = uno(sql_huerfanas(j["base"], j["col_base"], j["unida"],
                                                  j["col_unida"], dialecto))
        except Exception as e:                   # noqa: BLE001 — se muestra, no se oculta
            fila.update(estado="no_verificable", motivo="error_motor", error=str(e)[:300])
            continue
        rel = clasificar(fila["repetidas_base"] == 0, fila["repetidas_unida"] == 0)
        fila["relacion"] = rel
        if rel == "N:N":
            fila.update(estado="error", motivo="nn")
        elif rel == "1:N":
            fila.update(estado="revisar", motivo="1n")
        elif fila["huerfanas"] and j["tipo"] in ("INNER", "RIGHT"):
            fila.update(estado="revisar", motivo="huerfanas_inner")
        elif fila["huerfanas"]:
            fila.update(estado="revisar", motivo="huerfanas_left")
        else:
            fila.update(estado="ok", motivo="ok")
    return salida


# ──────────────────────────────────────────────────────────────
# 4) Semáforo
# ──────────────────────────────────────────────────────────────

def semaforo(perfil, duplicadas=0, joins=None):
    """ok / revisar / error para el resultado entero."""
    joins = joins or []
    if any(j.get("estado") == "error" for j in joins):
        return "error"
    if (duplicadas
            or any(j.get("estado") == "revisar" for j in joins)
            or any(SEVERIDAD.get(a) == "revisar" for f in perfil for a in f["alertas"])):
        return "revisar"
    return "ok"


def a_dataframe(perfil, etiquetas=None, textos_alerta=None):
    """El perfil como DataFrame para mostrar/exportar.

    `etiquetas`: nombres de columna traducidos (dict clave→texto).
    `textos_alerta`: código de alerta → texto traducido.
    """
    etiquetas = etiquetas or {}
    textos_alerta = textos_alerta or {}
    filas = []
    for f in perfil:
        fila = {etiquetas.get(k, k): v for k, v in f.items() if k != "alertas"}
        fila[etiquetas.get("alertas", "alertas")] = "; ".join(
            textos_alerta.get(a, a) for a in f["alertas"])
        filas.append(fila)
    return pd.DataFrame(filas)
