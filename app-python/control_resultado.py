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
    if pd.api.types.is_bool_dtype(serie):
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
        m = _ISO.match(v) or _DMY.match(v)
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
    if all(isinstance(v, str) and _ISO.match(v) for v in fechas):
        clave = str                     # ISO: el orden de texto es el cronológico
    elif all(isinstance(v, (datetime, date)) for v in fechas):
        clave = None
    else:
        clave = _clave_dmy
    mn = min(fechas, key=clave) if clave else min(fechas)
    mx = max(fechas, key=clave) if clave else max(fechas)
    return [a for a in anios if a is not None], _valor_legible(mn), _valor_legible(mx)


def _clave_dmy(v):
    if isinstance(v, (datetime, date)):
        return (v.year, v.month, v.day)
    m = _ISO.match(v)
    if m:
        return tuple(int(x) for x in m.groups())
    d, mth, y = (int(x) for x in re.findall(r"\d+", v)[:3])
    return (y, mth, d)


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
    for nombre in df.columns:
        serie = df[nombre]
        if isinstance(serie, pd.DataFrame):      # nombre de columna repetido
            serie = serie.iloc[:, 0]
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
        if pd.api.types.is_bool_dtype(serie):
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

_ID = r'(?:\[[^\]]+\]|"[^"]+"|`[^`]+`|[A-Za-z_][\w$]*)'
_QUAL = rf"{_ID}(?:\s*\.\s*{_ID}){{0,2}}"

#: Palabras que pueden seguir a un nombre de tabla y NO son un alias.
_NO_ALIAS = {
    "where", "join", "inner", "left", "right", "full", "cross", "outer", "on",
    "group", "order", "having", "limit", "offset", "union", "except", "intersect",
    "with", "natural", "using", "fetch", "window", "qualify", "as",
}

_NO_ALIAS_RX = "|".join(sorted(_NO_ALIAS))
# El alias no puede ser una palabra clave: sin el lookahead, en «FROM ventas
# JOIN precios» el regex se comía el JOIN como alias y ese join no existía.
_REF_TABLA = re.compile(
    rf"\b(?P<kw>from|join)\s+(?P<tabla>{_QUAL})"
    rf"(?:\s+(?:as\s+)?(?!(?:{_NO_ALIAS_RX})\b)(?P<alias>{_ID}))?",
    re.IGNORECASE)
_ON = re.compile(
    r"\bon\b(?P<cond>.*?)(?=\b(?:join|inner|left|right|full|cross|where|group|order|"
    r"having|union|limit|except|intersect)\b|$)",
    re.IGNORECASE | re.DOTALL)
_IGUALDAD = re.compile(rf"(?P<a>{_QUAL})\s*=\s*(?P<b>{_QUAL})")
_TIPO_JOIN = re.compile(r"\b(left|right|full|cross|inner)?\s*(?:outer\s+)?join\s*$",
                        re.IGNORECASE)
_CTE = re.compile(rf"(?:\bwith\b|,)\s*(?P<n>{_ID})\s*(?:\([^)]*\))?\s+as\s*\(", re.IGNORECASE)


def _limpio(identificador):
    return identificador.strip().strip('[]"`')


def _partes(calificado):
    return [_limpio(p) for p in re.split(r"\s*\.\s*", calificado.strip())]


def _alias_valido(alias):
    return bool(alias) and alias.lower() not in _NO_ALIAS


def joins_del_sql(sql):
    """Los JOIN ... ON col = col del SQL.

    Devuelve una lista de dicts: tipo (INNER/LEFT/RIGHT/FULL), la tabla
    ya existente (`base`, `col_base`) y la que se une (`unida`,
    `col_unida`), como aparecen escritas en el SQL (con esquema, si lo
    llevan). Las claves compuestas (ON a.x = b.x AND a.y = b.y) quedan
    en un solo join con varias columnas.

    Un join cuyo lado es un CTE o una subconsulta se devuelve con
    `verificable=False`: su «tabla» no existe en la base para preguntarle.
    """
    texto = _sin_literales(_sin_comentarios(sql or ""))
    ctes = {m.group("n").strip('[]"`').lower() for m in _CTE.finditer(texto)}

    refs = []           # (posición, palabra, tabla escrita, alias)
    alias_a_tabla = {}
    for m in _REF_TABLA.finditer(texto):
        tabla = re.sub(r"\s*\.\s*", ".", m.group("tabla").strip())
        alias = m.group("alias")
        if not _alias_valido(alias):
            alias = None
        nombre_simple = _partes(tabla)[-1].lower()
        refs.append((m.start(), m.group("kw").lower(), tabla, alias))
        alias_a_tabla[nombre_simple] = tabla
        if alias:
            alias_a_tabla[_limpio(alias).lower()] = tabla

    joins = []
    for pos, kw, tabla, alias in refs:
        if kw != "join":
            continue
        previo = texto[max(0, pos - 30):pos + 4]
        tm = _TIPO_JOIN.search(previo)
        tipo = ((tm.group(1) or "inner") if tm else "inner").upper()
        if tipo == "CROSS":
            continue
        # La condición ON que sigue a ESTE join (hasta el próximo join).
        siguiente = min([p for p, *_ in refs if p > pos] or [len(texto)])
        tramo = texto[pos:siguiente]
        on = _ON.search(tramo)
        if not on:
            continue
        propio = {_partes(tabla)[-1].lower()}
        if alias:
            propio.add(_limpio(alias).lower())
        pares = []
        for ig in _IGUALDAD.finditer(on.group("cond")):
            a, b = _partes(ig.group("a")), _partes(ig.group("b"))
            if len(a) < 2 or len(b) < 2:
                continue            # comparación contra una constante o sin calificar
            lado_a, lado_b = a[-2].lower(), b[-2].lower()
            if lado_b in propio and lado_a not in propio:
                pares.append((lado_a, a[-1], b[-1]))
            elif lado_a in propio and lado_b not in propio:
                pares.append((lado_b, b[-1], a[-1]))
        if not pares:
            continue
        # Un join puede cruzar contra UNA sola tabla ya existente por vez;
        # si la condición mezcla dos, se toma la primera (la más común).
        otro = pares[0][0]
        pares = [p for p in pares if p[0] == otro]
        base = alias_a_tabla.get(otro, otro)
        verificable = (_partes(base)[-1].lower() not in ctes
                       and _partes(tabla)[-1].lower() not in ctes)
        joins.append({
            "tipo": tipo, "base": base, "col_base": [p[1] for p in pares],
            "unida": tabla, "col_unida": [p[2] for p in pares],
            "verificable": verificable,
        })
    return joins


# ──────────────────────────────────────────────────────────────
# 3) Verificación de los joins contra la base
# ──────────────────────────────────────────────────────────────

_SEGURO = re.compile(rf"^{_QUAL}$")


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
    if re.fullmatch(r"[A-Za-z_][\w]*", col):
        return col
    if "sql server" in (dialecto or "").lower():
        return f"[{col}]"
    if "mysql" in (dialecto or "").lower():
        return f"`{col}`"
    return f'"{col}"'


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


def _es_pk(cols_catalogo, columnas):
    """La clave es la PK completa de la tabla (entonces es única sin preguntar)."""
    pks = {n for n, c in cols_catalogo.items() if c.get("pk")}
    return bool(pks) and pks == {c.lower() for c in columnas}


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
                    relacion=None, estado="no_verificable", motivo="cte", error=None)
        salida.append(fila)
        if not j["verificable"]:
            continue
        cat_b = _columnas_catalogo(catalogo, j["base"])
        cat_u = _columnas_catalogo(catalogo, j["unida"])
        if (cat_b is None or cat_u is None
                or not _SEGURO.match(j["base"]) or not _SEGURO.match(j["unida"])
                or any(c.lower() not in cat_b for c in j["col_base"])
                or any(c.lower() not in cat_u for c in j["col_unida"])):
            fila["motivo"] = "fuera_catalogo"
            continue
        try:
            fila["repetidas_unida"] = (0 if _es_pk(cat_u, j["col_unida"]) else
                                       uno(sql_claves_repetidas(j["unida"], j["col_unida"], dialecto)))
            fila["repetidas_base"] = (0 if _es_pk(cat_b, j["col_base"]) else
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
