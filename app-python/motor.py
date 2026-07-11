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

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from catalogo import catalogo_a_fichas
from proveedores_ia import completar


# ──────────────────────────────────────────────────────────────
# 1) RETRIEVAL (RAG) — TF-IDF local sobre las fichas del esquema
# ──────────────────────────────────────────────────────────────
class RecuperadorEsquema:
    def __init__(self, fichas):
        self.fichas = fichas
        self.textos = [f["texto"] for f in fichas]
        self.vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2),
                                   token_pattern=r"[a-zA-Zàáâãéêíóôõúüçñ_]+")
        self.matriz = self.vec.fit_transform(self.textos)

    def recuperar(self, pregunta, k=4):
        """Devuelve (fichas_top_k, similitudes_top_k)."""
        q = self.vec.transform([pregunta])
        sims = cosine_similarity(q, self.matriz)[0]
        idx = sims.argsort()[::-1][:max(k, 3)]
        return [self.fichas[i] for i in idx], [float(sims[i]) for i in idx]


# ──────────────────────────────────────────────────────────────
# 2) GENERACIÓN SQL (multi-proveedor, con CTE y autoevaluación)
# ──────────────────────────────────────────────────────────────
SYSTEM_SQL = """Sos un experto en SQL que traduce preguntas en lenguaje natural a consultas SQL de nivel profesional. La pregunta puede venir en español, inglés o portugués.

REGLAS ESTRICTAS:
1. Usá EXCLUSIVAMENTE las tablas y columnas del esquema provisto. NUNCA inventes nombres.
2. El motor es {dialecto}. Usá exactamente su sintaxis.
3. OPTIMIZACIÓN: si la consulta requiere agregaciones intermedias, subconsultas repetidas o pasos lógicos, estructurala con CTEs (WITH ... AS) con nombres descriptivos. Preferí CTE a subconsultas anidadas. Evitá SELECT *: listá solo las columnas necesarias. Filtrá lo antes posible (predicados en el WHERE más interno). Nunca apliques funciones sobre columnas indexables en el WHERE: usá rangos (col >= 'inicio' AND col < 'fin').
4. Si la pregunta pide ranking o "top", agregá ORDER BY y limitá filas.
5. Usá JOINs explícitos según las relaciones del esquema.
6. Filtrá registros anulados/eliminados si existe la columna (anulada=0, deleted=0, activo=1).
7. Solo SELECT (o WITH ... SELECT). Nunca INSERT/UPDATE/DELETE/DROP/ALTER/EXEC.
8. Alias legibles en español para columnas calculadas (total_cobrado, promedio_mensual).

FORMATO DE RESPUESTA — devolvé EXACTAMENTE esto, sin markdown ni explicación extra:
SQL:
<la consulta>
CONFIANZA: <entero 0-100: qué tan seguro estás de que la consulta responde exactamente la pregunta con este esquema>
SUPUESTOS: <si asumiste algo (interpretación de fechas, qué columna usar), listalo en una línea; si no, "ninguno">

ESQUEMA DISPONIBLE (usá solo esto):
{esquema}
"""

SYSTEM_EXPLICAR = """Sos un analista de datos. Te paso una pregunta de un usuario de negocio, el SQL ejecutado y una muestra del resultado. Explicá el resultado en 2-4 frases claras en el MISMO idioma de la pregunta, con números concretos. No expliques el SQL: explicá QUÉ dice el dato. Si el resultado está vacío, decilo y sugerí por qué puede ser."""

SYSTEM_PROCEDURE = """Sos un DBA experto. Convertí la consulta SELECT provista en un STORED PROCEDURE de nivel producción para {dialecto}, llamado {nombre}. Parametrizá las fechas y filtros literales que encuentres como parámetros con valores default sensatos. Incluí comentario de cabecera (propósito, parámetros, autor: MV SQL NLP). Devolvé SOLO el código SQL del procedure, sin markdown."""


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
PALABRAS_PROHIBIDAS = ["insert ", "update ", "delete ", "drop ", "alter ",
                       "truncate ", "create ", "exec ", "execute ", "merge ",
                       "grant ", "revoke ", "xp_", "sp_executesql"]

PALABRAS_SQL = {
    # keywords/aliases que el extractor de "tablas" puede confundir
    "select", "where", "group", "order", "having", "limit", "offset", "union",
    "unnest", "generate_series", "dual", "values", "lateral",
}


def validar_sql(sql, catalogo, ctes=None):
    """Devuelve (es_valido, problemas, advertencias)."""
    problemas, advertencias = [], []
    s = sql.lower()

    for p in PALABRAS_PROHIBIDAS:
        if p in s:
            problemas.append(f"Operación no permitida: '{p.strip()}' — MV SQL NLP es solo lectura.")
    inicio = s.lstrip()[:8]
    if not (inicio.startswith("select") or inicio.startswith("with")):
        problemas.append("La consulta debe empezar con SELECT o WITH (CTE).")

    # nombres de CTE definidos en la consulta cuentan como tablas válidas
    nombres_cte = set(re.findall(r"(?:with|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", s))

    tablas_catalogo = {t.lower() for t in catalogo["tablas"].keys()}
    tablas_en_sql = set(re.findall(r"(?:from|join)\s+\[?([a-zA-Z_][a-zA-Z0-9_.]*)\]?", s))
    for t in tablas_en_sql:
        t_simple = t.split(".")[-1]
        if t_simple in PALABRAS_SQL or t_simple in nombres_cte:
            continue
        if t_simple not in tablas_catalogo:
            problemas.append(f"Tabla inexistente en el catálogo: '{t}'")

    columnas_catalogo = set()
    for info in catalogo["tablas"].values():
        for c in info["columnas"]:
            columnas_catalogo.add(c["columna"].lower())

    posibles = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*\.([a-zA-Z_][a-zA-Z0-9_]*)", s)
    for col in set(posibles):
        if col not in columnas_catalogo and col != "*" and col not in PALABRAS_SQL:
            advertencias.append(f"Columna no reconocida en el catálogo: '{col}' (puede ser alias de CTE)")

    return len(problemas) == 0, problemas, advertencias


# ──────────────────────────────────────────────────────────────
# 4) INTERVALO DE CONFIANZA
# ──────────────────────────────────────────────────────────────
def calcular_confianza(conf_llm, sim_rag, es_valido, n_advertencias, usa_cte):
    """
    Combina señales independientes en un puntaje 0-100 con intervalo.

      55%  autoevaluación del modelo (qué tan seguro dijo estar)
      25%  señal del RAG (similitud pregunta<->esquema recuperado)
      20%  validación estructural (catálogo + advertencias)

    El intervalo (±) refleja cuánta información tenemos: sin
    autoevaluación del modelo el intervalo se ensancha.
    """
    base_llm = conf_llm if conf_llm is not None else 60
    senal_rag = min(1.0, (sim_rag or 0) * 3.0) * 100      # sim>0.33 satura en 100
    senal_val = (100 if es_valido else 20) - min(30, n_advertencias * 10)

    puntaje = 0.55 * base_llm + 0.25 * senal_rag + 0.20 * max(0, senal_val)
    if usa_cte:
        puntaje = min(100, puntaje + 2)   # estructura explícita: leve bonus

    margen = 5
    if conf_llm is None:
        margen += 7
    if (sim_rag or 0) < 0.05:
        margen += 5
    if n_advertencias:
        margen += 3

    puntaje = round(max(5, min(99, puntaje)))
    return {
        "puntaje": puntaje,
        "margen": margen,
        "intervalo": (max(0, puntaje - margen), min(100, puntaje + margen)),
        "componentes": {
            "modelo": round(base_llm),
            "rag": round(senal_rag),
            "validacion": round(max(0, senal_val)),
        },
    }


# ──────────────────────────────────────────────────────────────
# 5) MOTOR COMPLETO
# ──────────────────────────────────────────────────────────────
class MotorMVSQL:
    """
    Motor principal. Recibe una ConexionBD ya conectada (conectores.py)
    y la configuración del proveedor de IA elegido por el cliente.
    """

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

    def _completar(self, system, user, max_tokens=1500):
        return completar(self.ia["proveedor"], self.ia.get("api_key"),
                         system, user, modelo=self.ia.get("modelo"),
                         base_url=self.ia.get("base_url"), max_tokens=max_tokens)

    def responder(self, pregunta, k=4, limite=5000, explicar=True):
        resultado = {
            "pregunta": pregunta, "tablas_recuperadas": [], "sql": None,
            "valido": False, "problemas": [], "advertencias": [],
            "confianza": None, "supuestos": "", "columnas": None, "filas": None,
            "sql_ejecutado": None, "error": None, "explicacion": None,
            "usa_cte": False,
        }

        # 1) RAG
        relevantes, sims = self.recuperador.recuperar(pregunta, k=k)
        resultado["tablas_recuperadas"] = [f["tabla"] for f in relevantes]
        sim_top = sims[0] if sims else 0.0

        # 2) generación
        esquema = "\n\n".join(f["texto"] for f in relevantes)
        system = SYSTEM_SQL.format(dialecto=self.cx.dialecto, esquema=esquema)
        crudo = self._completar(system, pregunta)
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
            correccion = (f"{pregunta}\n\nTu consulta anterior fue:\n{sql}\n\n"
                          f"Fue RECHAZADA por estos problemas:\n- " + "\n- ".join(problemas) +
                          "\nGenerá una consulta corregida usando SOLO tablas y columnas del esquema.")
            try:
                crudo2 = self._completar(system, correccion)
                sql2, conf_llm2, supuestos2 = _parsear_respuesta_sql(crudo2)
                ok2, prob2, adv2 = validar_sql(sql2, self.catalogo)
                if ok2:
                    sql, conf_llm, supuestos = sql2, conf_llm2, supuestos2
                    es_valido, problemas, advertencias = ok2, prob2, adv2
                    resultado.update(sql=sql, supuestos=supuestos, valido=True,
                                     problemas=[], advertencias=adv2,
                                     usa_cte=sql.lower().lstrip().startswith("with"))
            except Exception:
                pass  # el reintento es best-effort

        # 4) confianza
        resultado["confianza"] = calcular_confianza(
            conf_llm, sim_top, es_valido, len(resultado["advertencias"]),
            resultado["usa_cte"])

        # 5) ejecución
        if es_valido:
            try:
                cols, filas, sql_exec = self.cx.ejecutar(sql, limite=limite)
                resultado["columnas"] = cols
                resultado["filas"] = filas
                resultado["sql_ejecutado"] = sql_exec
            except Exception as e:
                resultado["error"] = str(e)

        # 6) explicación en lenguaje natural
        if explicar and resultado["filas"] is not None:
            try:
                muestra = _muestra_texto(resultado["columnas"], resultado["filas"])
                resultado["explicacion"] = self._completar(
                    SYSTEM_EXPLICAR,
                    f"PREGUNTA: {pregunta}\n\nSQL:\n{sql}\n\nRESULTADO ({len(resultado['filas'])} filas):\n{muestra}",
                    max_tokens=400)
            except Exception:
                pass

        return resultado

    def generar_stored_procedure(self, sql, nombre="sp_mvsql_consulta"):
        """Convierte una consulta guardada en stored procedure del dialecto activo."""
        system = SYSTEM_PROCEDURE.format(dialecto=self.cx.dialecto, nombre=nombre)
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
