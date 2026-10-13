# © 2026 Martín Viera. Todos los derechos reservados.

"""
motor.py — MV SQL NLP
==================================================================
Motor NL2SQL multi-proveedor con RAG sobre el catálogo del esquema.

Flujo:
  pregunta (lenguaje natural, ES/EN/PT)
    -> RAG: recuperar tablas relevantes (TF-IDF local, nada sale de tu red)
    -> IA (a elección del cliente): genera SQL optimizado con CTE
    -> Validador: cada tabla/columna debe existir en el catálogo
    -> Intervalo de confianza: qué tan segura es la traducción
    -> Ejecución segura (solo SELECT, tope de filas automático)
    -> Explicación en lenguaje natural del resultado
==================================================================
"""

import re

import mapa_semantico as MS
from catalogo import catalogo_a_fichas
from proveedores_ia import completar


# ──────────────────────────────────────────────────────────────
# 1) RETRIEVAL (RAG) — TF-IDF local sobre las fichas del esquema
# ──────────────────────────────────────────────────────────────
class RecuperadorEsquema:
    """RAG local: TF-IDF propio (sin sklearn) + mapa semántico.

    El TF-IDF anterior tokenizaba con [a-zA-Z_]+: «FactSales» era una sola
    palabra, «cliente_id» también, y el texto fijo de la ficha («Cantidad de
    filas», «Columnas», los tipos) pesaba más que los nombres. «ventas por
    cliente en 2024» y «sales by customer» daban similitud 0 contra una
    estrella en inglés, y el top-4 dejaba afuera la tabla de hechos.

    Ahora (mapa_semantico): los nombres se separan en palabras (snake, camel,
    dígitos), sin tildes y en singular; cada palabra suma su concepto de
    negocio ES/EN/PT (ventas = sales = vendas); la plantilla no se indexa; k
    se adapta a lo cerca que quedan las siguientes, y entran las tablas puente
    del camino de JOINs entre las elegidas.
    """

    def __init__(self, fichas):
        self.fichas = fichas
        self.textos = [f["texto"] for f in fichas]
        self.indice = MS.IndiceTfidf([MS.bolsa_de_ficha(f) for f in fichas])
        self.padres = {f["tabla"]: list(f.get("padres") or ()) for f in fichas}

    def recuperar(self, pregunta, k=4):
        """Devuelve (fichas, similitudes), de la más a la menos relevante."""
        sims = self.indice.similitudes(MS.analizar(pregunta or "", pregunta=True))
        idx = MS.elegir_tablas([f["tabla"] for f in self.fichas], sims, self.padres, k=k)
        return [self.fichas[i] for i in idx], [float(sims[i]) for i in idx]


# ──────────────────────────────────────────────────────────────
# 2) GENERACIÓN SQL (multi-proveedor, con CTE y autoevaluación)
# ──────────────────────────────────────────────────────────────
# Los prompts de sistema (SYSTEM_SQL/SYSTEM_EXPLICAR/SYSTEM_PROCEDURE) NO
# viven acá como constantes de módulo a propósito: eran importables con
# `import motor; motor.SYSTEM_SQL` — legibles con dos líneas de Python
# aunque este archivo esté compilado con Cython (tools/build_cython.py).
# Compilado o no, un atributo público de módulo siempre es introspectable.
# Viven como variables locales dentro de los métodos que los usan
# (MotorMVSQL.responder / .generar_stored_procedure): sin un nombre
# público que apunte a ellos, extraerlos requiere desensamblar la
# extensión compilada o interceptar la llamada real a la IA, no un
# `dir(motor)`.


def _parsear_respuesta_sql(texto):
    """Extrae (sql, confianza_llm, supuestos) del formato pedido al modelo."""
    texto = texto.strip()
    # limpiar fences por si el modelo desobedece
    texto = re.sub(r"```sql|```", "", texto, flags=re.IGNORECASE).strip()

    conf = None
    m = re.search(r"CONFIANZA:\s*(\d{1,3})", texto)
    if m:
        conf = max(0, min(100, int(m.group(1))))

    supuestos = ""
    m = re.search(r"SUPUESTOS:\s*(.+)", texto)
    if m:
        supuestos = m.group(1).strip()

    sql = texto
    m = re.search(r"SQL:\s*(.*?)(?:CONFIANZA:|$)", texto, flags=re.DOTALL)
    if m:
        sql = m.group(1).strip()
    else:
        # el modelo devolvió solo el SQL
        sql = re.split(r"CONFIANZA:", texto)[0].strip()
    return sql, conf, supuestos


# ──────────────────────────────────────────────────────────────
# 3) VALIDADOR contra el catálogo
# ──────────────────────────────────────────────────────────────
# Se buscan como PALABRA (token), nunca como subcadena, y fuera de literales,
# comentarios e identificadores citados. La lista vieja era de subcadenas
# con espacio: «r.last_update FROM», «fecha_insert» o un literal 'drop
# shipping' daban «Operación no permitida» sobre un SELECT legítimo.
# La barrera dura de solo lectura sigue en conectores.asegurar_solo_lectura.
PALABRAS_PROHIBIDAS = {"insert", "update", "delete", "drop", "alter", "truncate", "create", "exec",
                       "execute", "merge", "grant", "revoke", "into"}

PALABRAS_SQL = {
    # palabras que pueden aparecer donde va una tabla y no lo son
    "select", "where", "group", "order", "having", "limit", "offset", "union",
    "unnest", "generate_series", "dual", "values", "lateral",
}

# Tokens de SQL. Los literales, comentarios e identificadores citados se
# reconocen ANTES que las palabras: así nada de lo que tengan adentro se
# confunde con una palabra clave, una tabla o una columna.
_TOK_SQL = re.compile(r"""
    (?P<lit>'(?:[^']|'')*'?)
  | (?P<com>--[^\n]*|/\*.*?(?:\*/|\Z))
  | (?P<cit>"(?:[^"]|"")*"|\[[^\]]*\]|`[^`]*`)
  | (?P<num>\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+)
  | (?P<pal>[^\W\d][\w$]*)
  | (?P<op>::|<>|!=|<=|>=|\|\||[-+*/%=<>(),.;])
  | (?P<esp>\s+)
  | (?P<otro>.)
""", re.VERBOSE | re.DOTALL)

# Palabras del lenguaje (y partes de fecha, tipos, hints) que pueden aparecer
# sueltas sin ser columnas. Una que falte acá da, a lo sumo, una ADVERTENCIA.
_CLAVES_SQL = set("""
select from where group by order having limit offset fetch next first last only rows row ties top percent
with recursive materialized not as distinct all any some union intersect except minus join inner left right
full outer cross natural lateral apply on using and or in is null like ilike similar between exists case when
then else end asc desc nulls over partition range groups unbounded preceding following current filter within
window qualify true false unknown collate escape glob regexp rlike match div mod xor interval at zone time
timestamp date datetime year years month months day days hour hours minute minutes second seconds quarter
week weekday dow doy isodow isoyear epoch yy yyyy mm dd qq wk ww dw dy hh mi ss ms mcs ns microsecond
millisecond nanosecond dayofyear dayofweek dayofmonth weekofyear tzoffset iso_week isowk isoww both leading
trailing for placing cast as int integer bigint smallint tinyint numeric decimal real float double precision
varchar nvarchar char nchar text varying character boolean bool bit money smallmoney uuid json jsonb signed
unsigned binary varbinary blob clob current_date current_time current_timestamp localtime localtimestamp
sysdate systimestamp rownum rowid oid level nolock readuncommitted readpast holdlock updlock rowlock
tablock maxdop option recompile separator values default
""".split())

# Palabras tras las que un «(» NO abre una llamada a función.
_NO_FUNCION = set("""
in exists as any all some values over filter within using on and or not when then else select from join
where by having union intersect except with recursive lateral apply case is between like return returns
""".split())

# Palabras que pueden seguir a una tabla y no son su alias.
_NO_ALIAS = set("""
where join inner left right full cross outer on group order having limit offset union except intersect
with natural using fetch window qualify as hash loop merge remote apply pivot unpivot tablesample for
lateral set into select
""".split())

# Tipos de token que pueden cerrar una expresión: un nombre que les sigue
# directo es un alias implícito («SUM(x) total», «c.nombre cliente»).
_FIN_EXPRESION = {"pal", "cit", "num", "lit"}


def _tokens_sql(sql):
    """[(tipo, texto, normalizado)] sin espacios ni comentarios."""
    salida = []
    for m in _TOK_SQL.finditer(sql or ""):
        tipo = m.lastgroup
        if tipo in ("esp", "com"):
            continue
        txt = m.group()
        if tipo == "cit":
            norm = txt[1:-1].replace('""', '"').lower()
        else:
            norm = txt.lower()
        salida.append((tipo, txt, norm))
    return salida


def _es_nombre(tok):
    return tok[0] == "cit" or (tok[0] == "pal" and tok[2] not in _CLAVES_SQL)


def _analizar_sql(toks):
    """Estructura mínima del SQL para validarlo contra el catálogo.

    Devuelve un dict con: refs [(partes, alias)] de FROM/JOIN, ctes y sus
    columnas, definidos (alias de columnas, de tablas, de subconsultas y de
    ventanas), calificadas [(calificador, columna)] y sueltas [(norm, texto)].
    """
    n = len(toks)
    usados = set()               # índices que no son una columna suelta
    refs, ctes, cte_cols, definidos = [], set(), set(), set()

    # CTEs: «WITH [RECURSIVE] x [(a, b)] AS [NOT] [MATERIALIZED] (» y ventanas «WINDOW w AS (».
    for i in range(1, n):
        if toks[i - 1][2] not in ("with", "recursive", ",", "window") or toks[i][0] not in ("pal", "cit"):
            continue
        j, cols = i + 1, []
        if j < n and toks[j][1] == "(":
            k = j + 1
            while k < n and toks[k][1] != ")":
                if toks[k][0] in ("pal", "cit"):
                    cols.append(k)
                elif toks[k][1] != ",":
                    break
                k += 1
            if k >= n or toks[k][1] != ")":
                continue
            j = k + 1
        if j < n and toks[j][2] == "as":
            j += 1
            while j < n and toks[j][2] in ("not", "materialized"):
                j += 1
            if j < n and toks[j][1] == "(":
                (ctes if toks[i - 1][2] != "window" else definidos).add(toks[i][2])
                usados.add(i)
                for k in cols:
                    cte_cols.add(toks[k][2])
                    usados.add(k)

    # Paréntesis: función, subconsulta o agrupación.
    tipo_par, pila = {}, []
    for i, tok in enumerate(toks):
        if tok[1] == "(":
            sig = toks[i + 1][2] if i + 1 < n else ""
            prev = toks[i - 1] if i else None
            if sig in ("select", "with"):
                clase = "sub"
            elif prev and prev[0] in ("pal", "cit") and prev[2] not in _NO_FUNCION:
                clase = "func"
            else:
                clase = "grupo"
            pila.append(clase)
            tipo_par[i] = pila[:]
        elif tok[1] == ")":
            if pila:
                pila.pop()
        else:
            tipo_par[i] = pila[:]

    def leer_ref(j):
        if j < n and toks[j][2] == "lateral":
            j += 1
        if j >= n or toks[j][0] not in ("pal", "cit") or (toks[j][0] == "pal" and toks[j][2] in _CLAVES_SQL):
            return None, j
        partes = [j]
        j += 1
        while j + 1 < n and toks[j][1] == "." and toks[j + 1][0] in ("pal", "cit"):
            partes.append(j + 1)
            j += 2
        usados.update(partes)
        if j < n and toks[j][1] == "(":                  # función de tabla: generate_series(…), json_each(…)
            return None, j
        alias = None
        if j < n and toks[j][2] == "as":
            usados.add(j)
            j += 1
        if j < n and toks[j][0] in ("pal", "cit") and toks[j][2] not in _NO_ALIAS:
            alias = toks[j][2]
            usados.add(j)
            definidos.add(alias)
            j += 1
        refs.append(([toks[p] for p in partes], alias))
        return True, j

    for i, tok in enumerate(toks):
        if tok[2] == "from" and tok[0] == "pal":
            if "func" in (tipo_par.get(i) or [])[-1:]:
                continue                                 # EXTRACT(YEAR FROM x), TRIM(BOTH ' ' FROM x)…
            ok, j = leer_ref(i + 1)
            while ok and j < n and toks[j][1] == ",":
                ok, j = leer_ref(j + 1)
        elif tok[2] == "join" and tok[0] == "pal":
            leer_ref(i + 1)

    # Alias de columnas («expr AS x», «expr x») y de subconsultas («(…) s»).
    for i, tok in enumerate(toks):
        if i in usados or tok[0] not in ("pal", "cit"):
            continue
        prev = toks[i - 1] if i else None
        if prev and prev[2] == "as" and not (i + 1 < n and toks[i + 1][1] == "("):
            if not (prev[0] == "pal" and "func" in (tipo_par.get(i) or [])[-1:]):   # CAST(x AS INT)
                definidos.add(tok[2])
            usados.add(i)
        elif prev and _es_nombre(tok) and (
                prev[1] == ")" or prev[2] == "end" or (prev[0] in _FIN_EXPRESION and _es_nombre(prev))
                or prev[0] in ("num", "lit")):
            if not (i + 1 < n and toks[i + 1][1] in ("(", ".")):
                definidos.add(tok[2])
                usados.add(i)
        elif prev and prev[2] == "collate":
            usados.add(i)

    # Referencias a columnas.
    calificadas, sueltas = [], []
    i = 0
    while i < n:
        tok = toks[i]
        if i in usados or tok[0] not in ("pal", "cit"):
            i += 1
            continue
        if i + 1 < n and toks[i + 1][1] == ".":
            cadena = [tok]
            j = i + 1
            while j + 1 < n and toks[j][1] == "." and (toks[j + 1][0] in ("pal", "cit") or toks[j + 1][1] == "*"):
                cadena.append(toks[j + 1])
                j += 2
            if len(cadena) >= 2 and not (j < n and toks[j][1] == "("):   # esquema.funcion(…) no es columna
                calificadas.append(([c[2] for c in cadena[:-1]], cadena[-1]))
            i = j
            continue
        anterior = toks[i - 1] if i else None
        siguiente = toks[i + 1] if i + 1 < n else None
        if (tok[0] == "pal" and tok[2] in _CLAVES_SQL) or (siguiente and siguiente[1] == "(") or \
                (anterior and (anterior[1] == "::" or (anterior[0] == "otro" and anterior[1] in "@:$#?"))):
            i += 1
            continue
        sueltas.append((tok[2], tok[1]))
        i += 1

    return {"refs": refs, "ctes": ctes, "cte_cols": cte_cols, "definidos": definidos,
            "calificadas": calificadas, "sueltas": sueltas}


def validar_sql(sql, catalogo, ctes=None):
    """Devuelve (es_valido, problemas, advertencias).

    Problemas (rechazan): operaciones que no son de lectura, que no empiece
    con SELECT/WITH, tablas que no existen en el catálogo.
    Advertencias: columnas que no existen, o que existen pero en OTRA tabla
    que la del alias («p.ciudad» con p = pagos: ciudad está en clientes).

    Entiende identificadores citados ("x", [x], `x`), esquema.tabla, CTEs con
    lista de columnas y RECURSIVE, y el FROM de EXTRACT/TRIM/SUBSTRING.
    ctes: nombres extra que valen como tabla (por ejemplo, de un paso previo).
    """
    problemas, advertencias = [], []

    def problema(texto):
        if texto not in problemas:
            problemas.append(texto)

    def advertencia(texto):
        if texto not in advertencias:
            advertencias.append(texto)

    toks = _tokens_sql(sql)
    for tipo, txt, norm in toks:
        if tipo == "pal" and (norm in PALABRAS_PROHIBIDAS or norm.startswith("xp_") or norm == "sp_executesql"):
            problema(f"Operación no permitida: '{norm}' — MV SQL NLP es solo lectura.")
    if not toks or toks[0][2] not in ("select", "with"):
        problema("La consulta debe empezar con SELECT o WITH (CTE).")

    a = _analizar_sql(toks)
    tablas = catalogo.get("tablas", {})
    tablas_cat = {t.lower(): t for t in tablas}
    cols_de = {t: {c["columna"].lower() for c in info.get("columnas", [])} for t, info in tablas.items()}
    extra = {str(c).lower() for c in (ctes or ())}
    cte_ok = a["ctes"] | extra

    alias_a = {}                  # alias o nombre (minúscula) → {tablas reales} ; "<cte>" si es un CTE
    usadas = []
    for partes, alias in a["refs"]:
        completo = ".".join(p[2] for p in partes)
        ultimo = partes[-1][2]
        real = tablas_cat.get(completo) or tablas_cat.get(ultimo)
        if real:
            if real not in usadas:
                usadas.append(real)
            for clave in {alias, ultimo, real.lower()} - {None}:
                alias_a.setdefault(clave, set()).add(real)
        elif ultimo in cte_ok or completo in cte_ok:
            alias_a.setdefault(alias or ultimo, set()).add("<cte>")
        elif ultimo not in PALABRAS_SQL:
            problema(f"Tabla inexistente en el catálogo: '{'.'.join(p[1] for p in partes)}'")

    def donde_esta(col):
        return sorted(t for t in tablas if col in cols_de[t])

    for calificador, (tipo, txt, col) in a["calificadas"]:
        q = calificador[-1]
        destinos = alias_a.get(q)
        if destinos is None:
            if q in tablas_cat:
                destinos = {tablas_cat[q]}
            elif q in cte_ok or q in a["definidos"]:
                continue                                  # CTE o subconsulta: sus columnas no están en el catálogo
            else:
                advertencia(f"Alias o tabla no definida en la consulta: '{q}' (en '{q}.{txt}')")
                continue
        if "<cte>" in destinos or txt == "*":
            continue
        if any(col in cols_de[t] for t in destinos):
            continue
        en = ", ".join(sorted(destinos))
        otras = donde_esta(col)
        if otras:
            advertencia(f"La columna '{txt}' no existe en la tabla '{en}' (alias '{q}'); "
                        f"está en: {', '.join(otras)}")
        else:
            advertencia(f"Columna no reconocida en el catálogo: '{txt}' (tabla '{en}')")

    en_consulta = set().union(*(cols_de[t] for t in usadas)) if usadas else set()
    todas = set().union(*cols_de.values()) if cols_de else set()
    conocidos = a["definidos"] | a["cte_cols"] | cte_ok | set(tablas_cat)
    for norm, txt in a["sueltas"]:
        if norm in conocidos or norm in en_consulta or norm in PALABRAS_PROHIBIDAS:
            continue
        if not usadas and norm in todas:
            continue                                      # FROM sólo de CTEs/subconsultas: no se puede saber más
        otras = donde_esta(norm)
        if otras:
            advertencia(f"La columna '{txt}' no está en las tablas de la consulta "
                        f"({', '.join(usadas) or 'ninguna del catálogo'}); está en: {', '.join(otras)}")
        else:
            advertencia(f"Columna no reconocida en el catálogo: '{txt}'")

    return len(problemas) == 0, problemas, advertencias


# ──────────────────────────────────────────────────────────────
# 4) INTERVALO DE CONFIANZA
# ──────────────────────────────────────────────────────────────
def calcular_confianza(conf_llm, sim_rag, es_valido, n_advertencias, usa_cte,
                       cobertura=None, ejecucion=None, medidas_faltantes=0, joins_validos=None):
    """
    Combina señales independientes en un puntaje 0-100 con intervalo.

      40  autoevaluación del modelo (qué tan seguro dijo estar)
      20  validación contra el catálogo (y sus advertencias)
      20  ejecución: corrió, con filas, y trae cada medida pedida
      10  JOINs: fracción de los JOIN del SQL que siguen una relación del
          mapa semántico (FK declarada o deducida del nombre). Si el SQL no
          tiene JOIN (joins_validos=None) estos 10 se reparten entre los demás
      10  esquema: lo mejor entre la similitud TF-IDF y la cobertura (¿las
          tablas del SQL son las que trajo el RAG?)

    Topes, porque ahí ningún promedio puede tapar lo que pasó:
      - SQL rechazado por el validador: ≤ 30 (antes un SQL RECHAZADO y no
        ejecutado salía 76 % si el modelo decía 90);
      - error al ejecutar: ≤ 35;
      - JOINs fuera del mapa: ≤ 60 + 25 × fracción válida. Unir por una
        columna que no es una relación conocida es el error que más infla o
        achica totales sin tirar ningún error.

    La cobertura pesa 10 y no 20: el modelo sólo ve las tablas que trajo el
    RAG, así que casi siempre vale 1 — medía poco más que eso. Y usar CTE ya
    no suma: estructurar con WITH no hace más correcta la consulta
    (`usa_cte` queda en la firma por compatibilidad).

    El intervalo es `puntaje ± margen`, y el margen se angosta con cada
    evidencia que hay (el modelo dio su confianza, se ejecutó, los JOINs se
    verificaron contra el mapa).

    ejecucion: None (no se ejecutó), "ok", "vacio" o "error".
    """
    base_llm = conf_llm if conf_llm is not None else 60
    lexico = min(1.0, (sim_rag or 0) * 3.0)               # sim>0.33 satura
    senal_rag = max(lexico, cobertura if cobertura is not None else 0) * 100
    senal_val = max(0, (100 if es_valido else 0) - min(30, n_advertencias * 10))
    senal_ejec = {"ok": 100, "vacio": 55, "error": 0}.get(ejecucion, 60)
    senal_ejec = max(0, senal_ejec - 35 * medidas_faltantes)

    pesos = {"modelo": 0.40, "rag": 0.10, "validacion": 0.20, "ejecucion": 0.20}
    valores = {"modelo": base_llm, "rag": senal_rag, "validacion": senal_val, "ejecucion": senal_ejec}
    jv = None
    if joins_validos is not None:
        jv = max(0.0, min(1.0, float(joins_validos)))
        pesos["joins"] = 0.10
        valores["joins"] = jv * 100
    puntaje = sum(pesos[k] * valores[k] for k in pesos) / sum(pesos.values())
    if not es_valido:
        puntaje = min(puntaje, 30)        # rechazado: ni se ejecutó
    if ejecucion == "error":
        puntaje = min(puntaje, 35)        # si no corrió, no puede ser alta
    if jv is not None and jv < 1:
        puntaje = min(puntaje, 60 + 25 * jv)

    margen = 3
    if conf_llm is None:
        margen += 7
    if senal_rag < 15:
        margen += 5
    if n_advertencias:
        margen += 3
    if ejecucion is None:
        margen += 5                       # sin correrla sabemos menos
    if medidas_faltantes:
        margen += 4
    if jv is None:
        margen += 1                       # ningún JOIN verificado contra el mapa
    elif jv < 1:
        margen += 4

    puntaje = round(max(5, min(99, puntaje)))
    return {
        "puntaje": puntaje,
        "margen": margen,
        "intervalo": (max(0, puntaje - margen), min(100, puntaje + margen)),
        "componentes": {
            "modelo": round(base_llm),
            "rag": round(senal_rag),
            "validacion": round(senal_val),
            "ejecucion": round(senal_ejec),
            "joins": round(valores["joins"]) if jv is not None else None,
        },
    }


# Medidas que una pregunta puede pedir a la vez. «En unidades y en moneda»
# tiene que salir en DOS columnas: el modelo tendía a elegir una (o sumar
# unidades con dólares), y la pantalla no avisaba.
_MEDIDAS = {
    "unidades": (r"\bunidad(es)?\b|\bunits?\b|\bunidades\b|\bcantidad(es)?\b|"
                 r"\bquantity\b|\bquantidade\b|\bvolumen\b|\bvolume\b|\bpiezas\b"),
    "moneda": (r"\bmonto\b|\bimporte\b|\bmoneda\b|\bvalor(es)?\b|\bpesos\b|"
               r"\bd[oó]lar(es)?\b|\busd\b|\bu\$s\b|\bamount\b|\bcurrency\b|"
               r"\brevenue\b|\bfacturaci[oó]n\b|\bfaturamento\b|\breais\b|\$"),
}
_COL_MEDIDA = {
    "unidades": r"unid|units?|cant|qty|quant|volum|pieza",
    "moneda": r"usd|monto|importe|valor|value|amount|pesos|dolar|revenue|"
              r"factur|venta.*(usd|\$|monto)|\$|precio|price|moneda|reais",
}


def medidas_pedidas(pregunta):
    """Qué medidas pide la pregunta (sólo cuenta si pide más de una)."""
    q = (pregunta or "").lower()
    hay = [m for m, rx in _MEDIDAS.items() if re.search(rx, q)]
    return hay if len(hay) > 1 else []


def medidas_sin_columna(pedidas, columnas):
    """Medidas pedidas que no aparecen en ninguna columna del resultado."""
    cols = [str(c).lower() for c in (columnas or [])]
    return [m for m in pedidas
            if not any(re.search(_COL_MEDIDA[m], c) for c in cols)]


def _simple(nombre):
    return str(nombre).split(".")[-1].strip("[]\"`").lower()


def cobertura_esquema(sql, catalogo, recuperadas):
    """Fracción de las tablas del SQL que el RAG había recuperado.

    None si el SQL no nombra ninguna tabla del catálogo (no hay nada que
    medir: no se inventa una cobertura).
    """
    nombres = {_simple(t) for t in catalogo.get("tablas", {})}
    en_sql = {_simple(t) for t in re.findall(
        r"(?:from|join)\s+([\[\]\"`a-zA-Z_][\[\]\"`a-zA-Z0-9_.]*)", (sql or "").lower())}
    usadas = en_sql & nombres
    if not usadas:
        return None
    rec = {_simple(t) for t in recuperadas}
    return len(usadas & rec) / len(usadas)


# ──────────────────────────────────────────────────────────────
# 4b) CONTEXTO DEL NEGOCIO (mercados conformados)
# ──────────────────────────────────────────────────────────────
#: Hasta dónde se manda el texto de definiciones del negocio al prompt.
TOPE_CONOCIMIENTO = 12_000
#: Una pregunta de mercado o de share: ahí van siempre las tablas de mercados conformados.
_PREGUNTA_DE_MERCADO = re.compile(
    r"mercad|market|share|\bms\b|ms ?%|particip|cuota|canasta|conformad|competid|competencia|concorr",
    re.IGNORECASE)
_COLUMNA_CONFORMADA = re.compile(r"conformad|conformed", re.IGNORECASE)


def columnas_de_mercado_conformado(catalogo, excluir=()):
    """«tabla.columna» (o «tabla (tabla)») donde el modelo de origen ya trae el mercado conformado aplicado."""
    salida = []
    for tabla, info in catalogo["tablas"].items():
        if tabla in excluir:
            continue
        if _COLUMNA_CONFORMADA.search(tabla):
            salida.append(f"{tabla} (tabla)")
            continue
        for c in info["columnas"]:
            if _COLUMNA_CONFORMADA.search(c["columna"]):
                salida.append(f"{tabla}.{c['columna']}")
    return salida


# ──────────────────────────────────────────────────────────────
# 5) MOTOR COMPLETO
# ──────────────────────────────────────────────────────────────
class MotorMVSQL:
    """
    Motor principal. Recibe una ConexionBD ya conectada (conectores.py)
    y la configuración del proveedor de IA elegido por el cliente.
    """

    # Sin contexto del negocio hasta que alguien lo sume (sumar_contexto). En la
    # clase, y no sólo en __init__, para que un motor armado a mano también los tenga.
    conocimiento = ""
    tablas_clave = ()

    def __init__(self, conexion, ia):
        """
        conexion: ConexionBD conectada.
        ia: dict {proveedor, api_key, modelo, base_url}
        """
        self.cx = conexion
        self.ia = ia
        self.catalogo = conexion.extraer_catalogo()
        self.fichas = catalogo_a_fichas(self.catalogo)
        self.recuperador = RecuperadorEsquema(self.fichas)
        # Definiciones del negocio que trae otro programa (la suite: mercados
        # conformados, glosario). Van al prompt; no son datos de la base.
        self.conocimiento = ""
        self.tablas_clave = []

    def sumar_contexto(self, conocimiento="", relaciones=(), tablas_clave=()):
        """Suma lo que el esquema solo no dice: definiciones del negocio, JOINs del modelo y tablas de referencia.

        Se llama DESPUÉS del recorte de tablas del rol: las relaciones y las
        tablas clave que nombran algo que este usuario no ve se descartan, así
        la IA no se entera de que existen.

        conocimiento: texto (mercados conformados, glosario…), recortado a
            TOPE_CONOCIMIENTO para no comerse el contexto de la IA.
        relaciones: [{tabla_origen, columna_origen, tabla_destino,
            columna_destino}] del modelo de origen. Entran al catálogo como
            FKs y salen en las fichas («Relaciones (JOINs)»): sin ellas la IA
            adivina los JOIN por el nombre de las columnas.
        tablas_clave: tablas que acompañan siempre a una pregunta de mercado
            o share, aunque el buscador TF-IDF no las elija.
        """
        texto = str(conocimiento or "").strip()
        if len(texto) > TOPE_CONOCIMIENTO:
            texto = texto[:TOPE_CONOCIMIENTO].rsplit("\n", 1)[0] + "\n[…definiciones recortadas]"
        self.conocimiento = texto
        cols = {t: {c["columna"] for c in info["columnas"]} for t, info in self.catalogo["tablas"].items()}
        existentes = {(f["tabla_origen"], f["columna_origen"], f["tabla_destino"], f["columna_destino"])
                      for f in self.catalogo["fks"]}
        nuevas = []
        for r in relaciones or ():
            clave = (r.get("tabla_origen"), r.get("columna_origen"), r.get("tabla_destino"),
                     r.get("columna_destino"))
            if (clave[1] in cols.get(clave[0], ()) and clave[3] in cols.get(clave[2], ())
                    and clave not in existentes):
                existentes.add(clave)
                nuevas.append(dict(zip(("tabla_origen", "columna_origen", "tabla_destino", "columna_destino"),
                                       clave)))
        if nuevas:
            self.catalogo["fks"] = list(self.catalogo["fks"]) + nuevas
            self.fichas = catalogo_a_fichas(self.catalogo)
            self.recuperador = RecuperadorEsquema(self.fichas)
        self.tablas_clave = [t for t in tablas_clave or () if t in self.catalogo["tablas"]]
        return len(nuevas)

    def mapa(self):
        """Mapa semántico del catálogo ACTUAL (mapa_semantico.construir_mapa).

        Se rearma solo si el catálogo cambió: lo reemplaza el recorte por rol
        (app.py) o le suma relaciones sumar_contexto. Como sale del catálogo
        ya recortado, nunca nombra una tabla que el usuario no ve.
        """
        cat = self.catalogo
        huella = (id(cat), len(cat.get("tablas", {})), len(cat.get("fks", [])))
        if getattr(self, "_mapa_huella", None) != huella:
            self._mapa_cache = MS.construir_mapa(cat)
            self._mapa_huella = huella
        return self._mapa_cache

    def _bloque_negocio(self):
        """El bloque de definiciones del negocio del prompt ('' si no hay ninguna)."""
        partes = [self.conocimiento] if self.conocimiento else []
        propias = columnas_de_mercado_conformado(self.catalogo, excluir=self.tablas_clave)
        if propias:
            partes.append("En ESTE esquema el mercado conformado ya viene del modelo en: " + ", ".join(propias)
                          + ". Usá eso para filtrar el mercado en vez de reconstruir la canasta.")
        if not partes:
            return ""
        return ("DEFINICIONES DEL NEGOCIO (de la empresa: usalas para interpretar la pregunta; las tablas y "
                "columnas siguen siendo SOLO las del esquema):\n" + "\n".join(partes) + "\n\n")

    def _con_tablas_clave(self, pregunta, relevantes, sims):
        """Suma las tablas clave a lo recuperado cuando la pregunta es de mercado o share."""
        if not (self.tablas_clave and _PREGUNTA_DE_MERCADO.search(pregunta or "")):
            return relevantes, sims
        ya = {f["tabla"] for f in relevantes}
        extra = [f for f in self.fichas if f["tabla"] in self.tablas_clave and f["tabla"] not in ya]
        return relevantes + extra, list(sims) + [0.0] * len(extra)

    def _completar(self, system, user, max_tokens=1500):
        return completar(self.ia["proveedor"], self.ia.get("api_key"),
                         system, user, modelo=self.ia.get("modelo"),
                         base_url=self.ia.get("base_url"), max_tokens=max_tokens)

    def responder(self, pregunta, k=4, limite=5000, explicar=True, contexto="",
                  privado=False):
        """
        contexto: preferencias del usuario (moneda, decimales, etc.) que se
        pasan a la IA como instrucción adicional — no forman parte de la
        pregunta guardada ni del historial.
        privado: modo privacidad estricta. Con True, al proveedor de IA se le
        manda el esquema SIN valores de ejemplo de las columnas (texto_min) y
        no se genera análisis del resultado (explicar se fuerza a False): así
        NINGUN dato real de la base sale, ni al generar el SQL ni después.
        """
        if privado:
            explicar = False
        resultado = {
            "pregunta": pregunta, "tablas_recuperadas": [], "sql": None,
            "valido": False, "problemas": [], "advertencias": [],
            "confianza": None, "supuestos": "", "columnas": None, "filas": None,
            "sql_ejecutado": None, "error": None, "explicacion": None,
            "usa_cte": False,
        }

        # 1) RAG
        relevantes, sims = self.recuperador.recuperar(pregunta, k=k)
        relevantes, sims = self._con_tablas_clave(pregunta, relevantes, sims)
        resultado["tablas_recuperadas"] = [f["tabla"] for f in relevantes]
        sim_top = sims[0] if sims else 0.0

        # 2) generación. En modo privado se usa texto_min (sin valores de
        # ejemplo): al proveedor de IA solo van nombres de tablas y columnas.
        _clave = "texto_min" if privado else "texto"
        esquema = "\n\n".join(f.get(_clave, f["texto"]) for f in relevantes)
        _system_sql = """Sos un experto en SQL que traduce preguntas en lenguaje natural a consultas SQL de nivel profesional. La pregunta puede venir en español, inglés o portugués.

REGLAS ESTRICTAS:
1. Usá EXCLUSIVAMENTE las tablas y columnas del esquema provisto. NUNCA inventes nombres.
2. El motor es {dialecto}. Usá exactamente su sintaxis.
3. OPTIMIZACIÓN: si la consulta requiere agregaciones intermedias, subconsultas repetidas o pasos lógicos, estructurala con CTEs (WITH ... AS) con nombres descriptivos. Preferí CTE a subconsultas anidadas. Evitá SELECT *: listá solo las columnas necesarias. Filtrá lo antes posible (predicados en el WHERE más interno). Nunca apliques funciones sobre columnas indexables en el WHERE: usá rangos (col >= 'inicio' AND col < 'fin').
4. Si la pregunta pide ranking o "top", agregá ORDER BY y limitá filas.
5. Usá JOINs explícitos y uní tablas SOLO por las relaciones del esquema o los "JOINs válidos" del MAPA SEMÁNTICO. Si dos tablas no se unen directo, seguí el camino que indica el mapa. Si un nombre lleva espacios o es palabra reservada, citalo como pide el dialecto.
6. Filtrá registros anulados/eliminados si existe la columna (anulada=0, deleted=0, activo=1).
7. Solo SELECT (o WITH ... SELECT). Nunca INSERT/UPDATE/DELETE/DROP/ALTER/EXEC.
8. Alias legibles en español para columnas calculadas (total_cobrado, promedio_mensual).
9. Si la pregunta pide VARIAS medidas (por ejemplo unidades Y monto/moneda), devolvé UNA COLUMNA POR MEDIDA, separadas y con alias que las nombren (total_unidades, total_monto_usd). Nunca elijas una sola ni sumes unidades con dinero. Si el esquema tiene la medida en varias monedas, una columna por moneda.

FORMATO DE RESPUESTA — devolvé EXACTAMENTE esto, sin markdown ni explicación extra:
SQL:
<la consulta>
CONFIANZA: <entero 0-100: qué tan seguro estás de que la consulta responde exactamente la pregunta con este esquema>
SUPUESTOS: <si asumiste algo (interpretación de fechas, qué columna usar), listalo en una línea; si no, "ninguno">

{negocio}ESQUEMA DISPONIBLE (usá solo esto):
{esquema}
{mapa}"""
        # El mapa semántico de las tablas recuperadas: roles, sinónimos y los
        # JOINs válidos — también los DEDUCIDOS, que antes se calculaban en el
        # catálogo (joins_inferidos) y nunca llegaban al prompt. En privado va
        # la versión mínima (JOINs y caminos); nunca lleva valores.
        bloque_mapa = MS.bloque_prompt(self.mapa(), resultado["tablas_recuperadas"], privado=privado)
        system = _system_sql.format(dialecto=self.cx.dialecto, esquema=esquema, negocio=self._bloque_negocio(),
                                    mapa=("\n" + bloque_mapa + "\n") if bloque_mapa else "")
        pregunta_ia = f"{pregunta}\n\n[Preferencias del usuario: {contexto}]" if contexto else pregunta
        crudo = self._completar(system, pregunta_ia)
        sql, conf_llm, supuestos = _parsear_respuesta_sql(crudo)
        resultado["sql"] = sql
        resultado["supuestos"] = supuestos
        resultado["usa_cte"] = sql.lower().lstrip().startswith("with")

        # 3) validación
        es_valido, problemas, advertencias = validar_sql(sql, self.catalogo)
        resultado["valido"] = es_valido
        resultado["problemas"] = problemas
        resultado["advertencias"] = advertencias

        # 3b) reintento automático si la validación falló (self-repair)
        if not es_valido:
            arreglado = self._reintentar_sql(system, pregunta_ia, sql, problemas)
            if arreglado:
                sql, conf_llm, supuestos, advertencias = arreglado
                es_valido, problemas = True, []
                resultado.update(sql=sql, supuestos=supuestos, valido=True,
                                 problemas=[], advertencias=advertencias,
                                 usa_cte=sql.lower().lstrip().startswith("with"))

        # 4) ejecución
        if es_valido:
            self._ejecutar_en(resultado, sql, limite)

        # 4b) ¿trae cada medida pedida? «unidades y moneda» son dos columnas.
        pedidas = medidas_pedidas(pregunta)
        faltan = (medidas_sin_columna(pedidas, resultado["columnas"])
                  if resultado["columnas"] is not None else [])
        if faltan:
            arreglado = self._reintentar_medidas(system, pregunta_ia, sql, faltan)
            if arreglado:
                sql2, conf2, sup2, adv2 = arreglado
                previo = dict(resultado)
                self._ejecutar_en(resultado, sql2, limite)
                faltan2 = medidas_sin_columna(pedidas, resultado["columnas"])
                if resultado["error"] is None and len(faltan2) < len(faltan):
                    sql, conf_llm, faltan = sql2, conf2, faltan2
                    resultado.update(sql=sql2, supuestos=sup2, advertencias=adv2,
                                     usa_cte=sql2.lower().lstrip().startswith("with"))
                else:
                    resultado.update({k: previo[k] for k in
                                      ("columnas", "filas", "sql_ejecutado", "error")})
        if faltan:
            resultado["advertencias"] = list(resultado["advertencias"]) + [
                "La pregunta pide " + " y ".join(pedidas) + ", pero el resultado "
                "no trae columna de: " + ", ".join(faltan) + "."]
        resultado["medidas_faltantes"] = faltan

        # 5) confianza, ya con lo que pasó al ejecutar
        if resultado["error"]:
            ejec = "error"
        elif resultado["filas"] is None:
            ejec = None
        else:
            ejec = "ok" if len(resultado["filas"]) else "vacio"
        # ¿Los JOIN del SQL siguen relaciones conocidas (declaradas o deducidas)?
        jv, fuera = MS.revisar_joins(sql, self.mapa()) if resultado["valido"] else (None, [])
        resultado["joins_validos"] = jv
        resultado["confianza"] = calcular_confianza(
            conf_llm, sim_top, resultado["valido"], len(resultado["advertencias"]),
            resultado["usa_cte"],
            cobertura=cobertura_esquema(sql, self.catalogo,
                                        resultado["tablas_recuperadas"]),
            ejecucion=ejec, medidas_faltantes=len(faltan), joins_validos=jv)
        if fuera:
            # Después de la confianza: ya pesa ahí (joins_validos), no se cuenta dos veces.
            resultado["advertencias"] = list(resultado["advertencias"]) + [
                f"JOIN fuera del mapa semántico (no es una relación declarada ni deducida): {j}" for j in fuera]

        # 6) explicación en lenguaje natural
        if explicar and resultado["filas"] is not None:
            resultado["explicacion"] = self._explicar_resultado(
                pregunta, sql, resultado, contexto)

        return resultado

    def _ejecutar_en(self, resultado, sql, limite):
        """Ejecuta (solo lectura) y deja columnas/filas/error en `resultado`."""
        resultado.update(columnas=None, filas=None, sql_ejecutado=None, error=None,
                         recorte=None)
        try:
            cols, filas, sql_exec = self.cx.ejecutar(sql, limite=limite)
            # Si un tope de rol recortó, el conector deja el total real:
            # viaja con el resultado para que la pantalla lo diga.
            resultado.update(columnas=cols, filas=filas, sql_ejecutado=sql_exec,
                             recorte=getattr(self.cx, "ultimo_recorte", None))
        except Exception as e:
            resultado["error"] = str(e)

    def _reintentar_medidas(self, system, pregunta_ia, sql, faltan):
        """Segunda vuelta cuando el SQL no trae todas las medidas pedidas.

        Devuelve (sql, confianza, supuestos, advertencias) si valida contra
        el catálogo, o None. Nunca se saltea la validación anti-alucinación.
        """
        pedido = (f"{pregunta_ia}\n\nTu consulta anterior fue:\n{sql}\n\n"
                  "No trae columna para: " + ", ".join(faltan) + ". La pregunta "
                  "pide esas medidas POR SEPARADO: devolvé una columna por cada "
                  "una, con alias que la nombre, usando SOLO el esquema.")
        try:
            sql2, conf2, sup2 = _parsear_respuesta_sql(self._completar(system, pedido))
            ok, _prob, adv = validar_sql(sql2, self.catalogo)
            if ok:
                return sql2, conf2, sup2, adv
        except Exception:
            pass
        return None

    def _reintentar_sql(self, system, pregunta_ia, sql, problemas):
        """Un intento de auto-corrección cuando el SQL no validó.

        Devuelve (sql, confianza, supuestos, advertencias) si la segunda
        vuelta sí valida, o None. Es best-effort: si el proveedor de IA
        falla, se sigue con el resultado original en vez de romper.
        """
        correccion = (f"{pregunta_ia}\n\nTu consulta anterior fue:\n{sql}\n\n"
                      f"Fue RECHAZADA por estos problemas:\n- " + "\n- ".join(problemas) +
                      "\nGenerá una consulta corregida usando SOLO tablas y columnas del esquema.")
        try:
            crudo = self._completar(system, correccion)
            sql2, conf2, supuestos2 = _parsear_respuesta_sql(crudo)
            ok, _prob, adv = validar_sql(sql2, self.catalogo)
            if ok:
                return sql2, conf2, supuestos2, adv
        except Exception:
            pass
        return None

    def _explicar_resultado(self, pregunta, sql, resultado, contexto):
        """Explicación en lenguaje natural de lo que dice el dato.

        Devuelve None si falla: la explicación es un extra, nunca puede
        tumbar una consulta que ya se ejecutó bien.
        """
        try:
            muestra = _muestra_texto(resultado["columnas"], resultado["filas"])
            extra = f"\n\nPREFERENCIAS DEL USUARIO: {contexto}" if contexto else ""
            _system_explicar = ("Sos un analista de datos. Te paso una pregunta de un "
                "usuario de negocio, el SQL ejecutado y una muestra del resultado. "
                "Explicá el resultado en 2-4 frases claras en el MISMO idioma de la "
                "pregunta, con números concretos. No expliques el SQL: explicá QUÉ dice "
                "el dato. Si el resultado está vacío, decilo y sugerí por qué puede ser.")
            return self._completar(
                _system_explicar,
                f"PREGUNTA: {pregunta}\n\nSQL:\n{sql}\n\nRESULTADO ({len(resultado['filas'])} filas):\n{muestra}{extra}",
                max_tokens=400)
        except Exception:
            return None

    def generar_stored_procedure(self, sql, nombre="sp_mvsql_consulta"):
        """Convierte una consulta guardada en stored procedure del dialecto activo."""
        _system_procedure = ("Sos un DBA experto. Convertí la consulta SELECT provista en un "
            "STORED PROCEDURE de nivel producción para {dialecto}, llamado {nombre}. "
            "Parametrizá las fechas y filtros literales que encuentres como parámetros con "
            "valores default sensatos. Incluí comentario de cabecera (propósito, parámetros, "
            "autor: MV SQL NLP). Devolvé SOLO el código SQL del procedure, sin markdown.")
        system = _system_procedure.format(dialecto=self.cx.dialecto, nombre=nombre)
        codigo = self._completar(system, sql, max_tokens=2000)
        return re.sub(r"```sql|```", "", codigo, flags=re.IGNORECASE).strip()

    def optimizar_sql(self, sql):
        """Reescribe una consulta existente optimizada con CTEs y buenas prácticas."""
        system = (f"Sos un optimizador de SQL para {self.cx.dialecto}. Reescribí la consulta "
                  "aplicando CTEs donde aporten claridad/performance, eliminando SELECT *, "
                  "y filtrando temprano. Mantené EXACTAMENTE la misma semántica. "
                  "Devolvé SOLO el SQL optimizado y después una línea 'CAMBIOS: ...' resumiendo qué mejoraste.")
        return self._completar(system, sql, max_tokens=2000)


def _muestra_texto(cols, filas, max_filas=20):
    lineas = [" | ".join(str(c) for c in cols)]
    for f in filas[:max_filas]:
        lineas.append(" | ".join(str(v) for v in f))
    if len(filas) > max_filas:
        lineas.append(f"... ({len(filas) - max_filas} filas más)")
    return "\n".join(lineas)
