# © 2026 Martín Viera. Todos los derechos reservados.

"""
esquema_visual.py — MV SQL NLP
==================================================================
Dos vistas sobre la base que el usuario de negocio sí aprovecha:

1. DIAGRAMA DE RELACIONES — cómo se conectan sus tablas. Sirve para
   entender la propia base (mucha gente no sabe qué se une con qué) y
   es lo primero que se mira en una implementación.

2. PLAN DE EJECUCIÓN (EXPLAIN) — por qué una consulta tarda, en
   castellano. No un volcado del motor: la lectura del volcado, con el
   problema y la recomendación.

Ambas funcionan sobre el catálogo que ya extrae conectores.py, así que
andan igual en SQLite, SQL Server, MySQL y PostgreSQL.
==================================================================
"""

import re

# ──────────────────────────────────────────────────────────────
# 1. Diagrama de relaciones (Mermaid: se dibuja sin dependencias)
# ──────────────────────────────────────────────────────────────
def diagrama_mermaid(catalogo: dict, tablas=None, max_columnas=8) -> str:
    """Diagrama entidad-relación en sintaxis Mermaid."""
    tablas_cat = catalogo.get("tablas", {})
    if tablas:
        elegidas = {t: v for t, v in tablas_cat.items() if t in set(tablas)}
    else:
        elegidas = tablas_cat
    if not elegidas:
        return ""

    lineas = ["erDiagram"]
    for tabla, info in elegidas.items():
        seguro = _id_mermaid(tabla)
        cols = info.get("columnas", [])[:max_columnas]
        if not cols:
            lineas.append(f"    {seguro} {{ }}")
            continue
        lineas.append(f"    {seguro} {{")
        for c in cols:
            tipo = _tipo_corto(c.get("tipo", ""))
            marca = " PK" if c.get("pk") else ""
            lineas.append(f"        {tipo} {_id_mermaid(c['columna'])}{marca}")
        if len(info.get("columnas", [])) > max_columnas:
            lineas.append(f"        mas mas_{len(info['columnas']) - max_columnas}_columnas")
        lineas.append("    }")

    vistas = set()
    for fk in catalogo.get("fks", []):
        origen, destino = fk.get("tabla"), fk.get("tabla_destino")
        if origen not in elegidas or destino not in elegidas:
            continue
        clave = (origen, destino, fk.get("columna", ""))
        if clave in vistas:
            continue
        vistas.add(clave)
        etiqueta = fk.get("columna", "fk").replace('"', "")
        lineas.append(f'    {_id_mermaid(destino)} ||--o{{ {_id_mermaid(origen)} : "{etiqueta}"')

    return "\n".join(lineas)


def _id_mermaid(nombre: str) -> str:
    """Mermaid no acepta espacios ni símbolos en los identificadores."""
    limpio = re.sub(r"\W", "_", str(nombre))
    return limpio or "sin_nombre"


def _tipo_corto(tipo: str) -> str:
    t = str(tipo).lower()
    if any(k in t for k in ("int", "serial", "number")):
        return "int"
    if any(k in t for k in ("char", "text", "varchar", "string")):
        return "texto"
    if any(k in t for k in ("date", "time")):
        return "fecha"
    if any(k in t for k in ("dec", "num", "float", "real", "money", "double")):
        return "decimal"
    if any(k in t for k in ("bit", "bool")):
        return "bool"
    return "dato"


def resumen_relaciones(catalogo: dict) -> list:
    """Relaciones en texto: (origen, columna, destino, columna_destino)."""
    filas = []
    for fk in catalogo.get("fks", []):
        filas.append((fk.get("tabla", ""), fk.get("columna", ""),
                      fk.get("tabla_destino", ""), fk.get("columna_destino", "")))
    return filas


def tablas_sin_relacion(catalogo: dict) -> list:
    """Tablas que no se unen con ninguna otra: suelen ser catálogos
    sueltos, tablas viejas o un problema de diseño que conviene ver."""
    conectadas = set()
    for fk in catalogo.get("fks", []):
        conectadas.add(fk.get("tabla"))
        conectadas.add(fk.get("tabla_destino"))
    return sorted(t for t in catalogo.get("tablas", {}) if t not in conectadas)


# ──────────────────────────────────────────────────────────────
# 2. Plan de ejecución, interpretado
# ──────────────────────────────────────────────────────────────
# Claves = nombre de motor (conexion.motor), NO el dialecto: antes se buscaba
# por dialecto.lower() ("postgresql", "sql server (t-sql)") contra claves que
# decían "postgres"/"mssql", así que el plan de ejecución de PostgreSQL nunca
# se encontraba y el cliente veía siempre "no disponible" sin explicación.
SQL_EXPLAIN = {
    "sqlite": "EXPLAIN QUERY PLAN {sql}",
    "sqlserver": None,      # requiere SET SHOWPLAN_ALL, sesión aparte
    "mysql": "EXPLAIN FORMAT=TRADITIONAL {sql}",
    "postgres": "EXPLAIN (ANALYZE false, VERBOSE false) {sql}",
}

# Señales de problema y su lectura en castellano.
SENALES = [
    (r"\bSCAN\b(?!.*USING)", "escaneo completo",
     "Se lee la tabla entera en vez de usar un índice.",
     "Si la consulta filtra por esa columna y la tabla es grande, un índice ahí puede cambiar segundos por milisegundos."),
    (r"\bALL\b", "escaneo completo",
     "El motor recorre todas las filas de la tabla.",
     "Revisar si el filtro del WHERE tiene un índice que lo acompañe."),
    (r"Seq Scan", "escaneo secuencial",
     "PostgreSQL lee la tabla completa.",
     "Normal en tablas chicas; en tablas grandes conviene un índice sobre la columna del filtro."),
    (r"USE TEMP B-TREE|Using temporary", "tabla temporal",
     "El motor arma una tabla temporal para ordenar o agrupar.",
     "Suele venir de un ORDER BY o GROUP BY sin índice que lo soporte."),
    (r"Using filesort", "ordenamiento en disco",
     "El ordenamiento no entra en memoria.",
     "Reducir las filas antes de ordenar, o indexar la columna del ORDER BY."),
    (r"CROSS JOIN|Nested Loop.*rows=\d{5,}", "producto cartesiano",
     "Se están cruzando muchas filas de dos tablas.",
     "Falta una condición de JOIN, o el JOIN no está usando la clave. Es el error que más cuelga consultas."),
]


def plan_de_ejecucion(conexion, sql: str):
    """Corre el EXPLAIN del motor y devuelve (filas_crudas, hallazgos).

    Nunca ejecuta la consulta real: solo pide el plan. Si el motor no lo
    soporta desde acá, devuelve ([], []) sin romper nada.
    """
    # Por motor (identificador canónico), con caída a inferirlo del dialecto
    # por si algún llamador pasa una conexión sin .motor.
    motor = getattr(conexion, "motor", "") or ""
    if not motor:
        d = getattr(conexion, "dialecto", "").lower()
        motor = ("sqlserver" if "server" in d else "postgres" if "postgre" in d
                 else "mysql" if "mysql" in d else "sqlite" if "sqlite" in d else "")
    plantilla = SQL_EXPLAIN.get(motor)
    if not plantilla:
        return [], []

    limpio = (sql or "").strip().rstrip(";")
    if not limpio:
        return [], []
    try:
        cur = getattr(conexion, '_con', None) or conexion.conn
        cur = cur.cursor()
        cur.execute(plantilla.format(sql=limpio))
        filas = [tuple(str(c) for c in fila) for fila in cur.fetchall()]
    except Exception:
        return [], []

    texto = " ".join(" ".join(f) for f in filas)
    hallazgos, vistos = [], set()
    for patron, titulo, que_pasa, que_hacer in SENALES:
        if re.search(patron, texto, re.IGNORECASE) and titulo not in vistos:
            vistos.add(titulo)
            hallazgos.append({"titulo": titulo, "que_pasa": que_pasa,
                              "que_hacer": que_hacer})
    return filas, hallazgos


def costo_estimado(filas_plan) -> str:
    """Lectura rápida del plan: liviano / medio / pesado."""
    if not filas_plan:
        return "desconocido"
    texto = " ".join(" ".join(f) for f in filas_plan).lower()
    escaneos = texto.count("scan") + texto.count("seq scan")
    if "cross join" in texto or escaneos >= 3:
        return "pesado"
    if escaneos >= 1 or "temp b-tree" in texto or "filesort" in texto:
        return "medio"
    return "liviano"


def diagrama_dot(catalogo: dict, tablas=None, max_columnas=8) -> str:
    """Mismo diagrama en formato DOT (Graphviz).

    Streamlit renderiza DOT de forma nativa con st.graphviz_chart, sin
    depender de librerías externas ni de que el navegador tenga Mermaid.
    """
    tablas_cat = catalogo.get("tablas", {})
    elegidas = ({t: v for t, v in tablas_cat.items() if t in set(tablas)}
                if tablas else tablas_cat)
    if not elegidas:
        return ""

    L = ['digraph esquema {',
         '  graph [rankdir=LR, bgcolor="transparent", pad=0.3, nodesep=0.5];',
         '  node  [shape=plaintext, fontname="Helvetica", fontsize=10,'
         ' fontcolor="#e2e8f0"];',
         '  edge  [color="#64748b", fontname="Helvetica", fontsize=8,'
         ' arrowhead=crow, arrowtail=none];']

    for tabla, info in elegidas.items():
        nid = _id_mermaid(tabla)
        cols = info.get("columnas", [])[:max_columnas]
        filas = "".join(
            f'<TR><TD ALIGN="LEFT" PORT="{_id_mermaid(c["columna"])}">'
            f'{"<B>" if c.get("pk") else ""}{_escapar(c["columna"])}'
            f'{"</B>" if c.get("pk") else ""}'
            f'  <FONT COLOR="#94a3b8" POINT-SIZE="8">{_tipo_corto(c.get("tipo",""))}</FONT>'
            f'</TD></TR>' for c in cols)
        restantes = len(info.get("columnas", [])) - len(cols)
        if restantes > 0:
            filas += (f'<TR><TD ALIGN="LEFT"><FONT COLOR="#94a3b8" POINT-SIZE="8">'
                      f'+{restantes} columnas más</FONT></TD></TR>')
        L.append(
            f'  {nid} [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" '
            f'CELLPADDING="4" BGCOLOR="#0f172a" COLOR="#334155">'
            f'<TR><TD BGCOLOR="#1e293b"><FONT COLOR="#38bdf8"><B>'
            f'{_escapar(tabla)}</B></FONT></TD></TR>{filas}</TABLE>>];')

    vistas = set()
    for fk in catalogo.get("fks", []):
        origen, destino = fk.get("tabla"), fk.get("tabla_destino")
        if origen not in elegidas or destino not in elegidas:
            continue
        clave = (origen, destino, fk.get("columna", ""))
        if clave in vistas:
            continue
        vistas.add(clave)
        L.append(f'  {_id_mermaid(destino)} -> {_id_mermaid(origen)} '
                 f'[label="{_escapar(fk.get("columna", ""))}"];')

    L.append("}")
    return "\n".join(L)


def _escapar(texto: str) -> str:
    """Escapa lo que rompería una etiqueta HTML de Graphviz."""
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
