"""
app.py — MV SQL NLP
==================================================================
Tu base de datos, en tu idioma. Consultá cualquier base SQL en
lenguaje natural, sin saber código.

  - Multi-IA: Claude, GPT, Gemini, Groq, Mistral, DeepSeek, Grok,
    Ollama local o cualquier endpoint compatible (elige el cliente)
  - Multi-BD: SQLite, SQL Server, MySQL/MariaDB, PostgreSQL
  - SQL optimizado con CTEs + validación contra el esquema real
  - Intervalo de confianza en cada respuesta
  - Consultas guardadas con nombre + generación de stored procedures
  - Exportación a Excel, CSV, PDF y HTML
  - Interfaz en español, inglés y portugués

Correr:  streamlit run app.py
==================================================================
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from conectores import ConexionBD, MOTORES
from exportar import a_csv, a_excel, a_pdf, a_html
from motor import MotorMVSQL
from proveedores_ia import PROVEEDORES, probar_conexion, cargar_licencia_creditos
import guardadas

# ──────────────────────────────────────────────────────────────
# IDIOMAS
# ──────────────────────────────────────────────────────────────
T = {
    "es": {
        "titulo": "MV SQL NLP", "sub": "Tu base de datos, en tu idioma. Preguntá en lenguaje natural — la IA genera SQL optimizado, lo valida contra tu esquema y te devuelve tablas, gráficos y análisis.",
        "config": "Configuración", "idioma": "Idioma", "ia": "Proveedor de IA",
        "modelo": "Modelo", "apikey": "API key", "probar": "Probar conexión",
        "bd": "Base de datos", "motor_bd": "Motor", "conectar": "Conectar",
        "tablas_ok": "tablas cargadas", "ver_esquema": "Ver esquema",
        "pregunta_ph": "Ej: ¿cuánto facturamos por mes este año, por sucursal?",
        "tu_pregunta": "Tu pregunta", "consultar": "Consultar",
        "ejemplos": "Ejemplos", "generando": "Generando SQL con IA y validando contra tu esquema…",
        "tablas_rag": "Tablas relevantes detectadas", "sql_gen": "SQL generado",
        "validado": "SQL validado contra el esquema real (sin nombres inventados)",
        "confianza": "Confianza", "supuestos": "Supuestos del modelo",
        "resultado": "Resultado", "filas": "Filas", "columnas": "Columnas",
        "tabla": "Tabla", "grafico": "Gráfico", "analisis": "Análisis",
        "exportar": "Exportar", "guardar": "Guardar consulta",
        "nombre_consulta": "Nombre de la consulta", "guardada": "Consulta guardada",
        "biblioteca": "Consultas guardadas", "ejecutar": "Ejecutar",
        "borrar": "Borrar", "sin_guardadas": "Todavía no guardaste consultas.",
        "sp": "Generar stored procedure", "sp_nombre": "Nombre del procedure",
        "optimizar": "Optimizar SQL (CTE)", "falta_key": "Configurá el proveedor de IA en la barra lateral.",
        "falta_bd": "Conectá una base de datos en la barra lateral.",
        "historial": "Historial", "descargar": "Descargar",
        "err_valid": "La validación encontró problemas:", "advertencias": "Advertencias",
        "sin_grafico": "No hay un gráfico automático para esta forma de datos.",
        "demo_hint": "¿Sin base propia? Usá la demo: motor SQLite, ruta cartera_demo.db (se genera con: python generar_db_demo.py).",
        "creditos_activos": "✓ Créditos activos — {n} incluidos ({plan})",
        "creditos_licencia": "Licencia de {email} · vence {vence}",
        "creditos_falta": "No se encontró licencia_mvsql.json en esta carpeta. Este proveedor solo funciona en el zip comprado con créditos embebidos.",
        "creditos_comprar": "[Comprar créditos]({url})",
        "fmt_titulo": "Formato de números", "fmt_dec": "Decimales",
        "fmt_miles": "Separador de miles", "fmt_estilo": "Estilo",
        "fmt_pct_dec": "Decimales en porcentajes", "fmt_moneda": "Moneda",
        "fmt_sin_moneda": "(sin moneda)",
        "fmt_moneda_todas": "Aplicar moneda a todas las columnas numéricas",
        "fmt_hint": "Se aplica a tablas, gráficos y a la respuesta de la IA.",
        "tipo_grafico": "Tipo de gráfico", "eje_x": "Eje X", "eje_y": "Eje Y",
        "g_auto": "✨ Automático (según los datos)", "g_barras": "Barras",
        "g_barras_h": "Barras horizontales", "g_linea": "Línea", "g_area": "Área",
        "g_torta": "Torta", "g_dispersion": "Dispersión", "g_histo": "Histograma",
        "archivo": "📄 Archivo (CSV / Excel / Parquet)",
        "subir_archivo": "Subí tu archivo",
        "archivo_hint": "El archivo se convierte a una base consultable al instante y queda en caché: la próxima carga es inmediata. Excel: cada hoja se vuelve una tabla.",
        "archivo_falta": "Subí un archivo primero.",
        "explorar": "Explorar", "eda_fuente": "Analizar",
        "eda_resultado": "El resultado actual",
        "eda_corr": "Correlación entre variables",
        "eda_infl": "Influencia de variables", "eda_objetivo": "Variable objetivo",
        "eda_infl_hint": "Importancia calculada con Random Forest sobre una muestra (hasta 5.000 filas): cuánto ayuda cada variable a predecir la variable objetivo.",
        "eda_pocas": "Se necesitan al menos 2 columnas numéricas con variación para este análisis.",
        "eda_shap_hint": "Valores SHAP sobre Random Forest (muestra de hasta 1.500 filas): el largo de la barra es cuánto influye; ▲ verde = al subir esa variable, sube {objetivo}; ▼ rojo = la reduce.",
        "eda_shap_falta": "Instalá el paquete 'shap' (pip install shap) para ver además la dirección del efecto.",
    },
    "en": {
        "titulo": "MV SQL NLP", "sub": "Your database, in your language. Ask in plain words — AI generates optimized SQL, validates it against your schema, and returns tables, charts and analysis.",
        "config": "Settings", "idioma": "Language", "ia": "AI provider",
        "modelo": "Model", "apikey": "API key", "probar": "Test connection",
        "bd": "Database", "motor_bd": "Engine", "conectar": "Connect",
        "tablas_ok": "tables loaded", "ver_esquema": "View schema",
        "pregunta_ph": "E.g.: monthly revenue this year, by branch?",
        "tu_pregunta": "Your question", "consultar": "Run",
        "ejemplos": "Examples", "generando": "Generating SQL with AI and validating against your schema…",
        "tablas_rag": "Relevant tables detected", "sql_gen": "Generated SQL",
        "validado": "SQL validated against the real schema (no invented names)",
        "confianza": "Confidence", "supuestos": "Model assumptions",
        "resultado": "Result", "filas": "Rows", "columnas": "Columns",
        "tabla": "Table", "grafico": "Chart", "analisis": "Analysis",
        "exportar": "Export", "guardar": "Save query",
        "nombre_consulta": "Query name", "guardada": "Query saved",
        "biblioteca": "Saved queries", "ejecutar": "Run",
        "borrar": "Delete", "sin_guardadas": "No saved queries yet.",
        "sp": "Generate stored procedure", "sp_nombre": "Procedure name",
        "optimizar": "Optimize SQL (CTE)", "falta_key": "Set up the AI provider in the sidebar.",
        "falta_bd": "Connect a database in the sidebar.",
        "historial": "History", "descargar": "Download",
        "err_valid": "Validation found problems:", "advertencias": "Warnings",
        "sin_grafico": "No automatic chart for this data shape.",
        "demo_hint": "No database yet? Use the demo: SQLite engine, path cartera_demo.db (generate it with: python generar_db_demo.py).",
        "creditos_activos": "✓ Active credits — {n} included ({plan})",
        "creditos_licencia": "License for {email} · expires {vence}",
        "creditos_falta": "licencia_mvsql.json not found in this folder. This provider only works in the zip purchased with embedded credits.",
        "creditos_comprar": "[Buy credits]({url})",
        "fmt_titulo": "Number format", "fmt_dec": "Decimals",
        "fmt_miles": "Thousands separator", "fmt_estilo": "Style",
        "fmt_pct_dec": "Decimals in percentages", "fmt_moneda": "Currency",
        "fmt_sin_moneda": "(no currency)",
        "fmt_moneda_todas": "Apply currency to every numeric column",
        "fmt_hint": "Applies to tables, charts and the AI answer.",
        "tipo_grafico": "Chart type", "eje_x": "X axis", "eje_y": "Y axis",
        "g_auto": "✨ Automatic (based on the data)", "g_barras": "Bars",
        "g_barras_h": "Horizontal bars", "g_linea": "Line", "g_area": "Area",
        "g_torta": "Pie", "g_dispersion": "Scatter", "g_histo": "Histogram",
        "archivo": "📄 File (CSV / Excel / Parquet)",
        "subir_archivo": "Upload your file",
        "archivo_hint": "The file becomes an instantly queryable base and is cached: the next load is immediate. Excel: each sheet becomes a table.",
        "archivo_falta": "Upload a file first.",
        "explorar": "Explore", "eda_fuente": "Analyze",
        "eda_resultado": "Current result",
        "eda_corr": "Correlation between variables",
        "eda_infl": "Variable influence", "eda_objetivo": "Target variable",
        "eda_infl_hint": "Importance computed with a Random Forest on a sample (up to 5,000 rows): how much each variable helps predict the target.",
        "eda_pocas": "At least 2 numeric columns with variation are needed for this analysis.",
        "eda_shap_hint": "SHAP values on a Random Forest (sample of up to 1,500 rows): bar length is how much it influences; ▲ green = increasing that variable increases {objetivo}; ▼ red = it decreases it.",
        "eda_shap_falta": "Install the 'shap' package (pip install shap) to also see the direction of the effect.",
    },
    "pt": {
        "titulo": "MV SQL NLP", "sub": "Seu banco de dados, no seu idioma. Pergunte em linguagem natural — a IA gera SQL otimizado, valida contra seu esquema e devolve tabelas, gráficos e análises.",
        "config": "Configuração", "idioma": "Idioma", "ia": "Provedor de IA",
        "modelo": "Modelo", "apikey": "API key", "probar": "Testar conexão",
        "bd": "Banco de dados", "motor_bd": "Motor", "conectar": "Conectar",
        "tablas_ok": "tabelas carregadas", "ver_esquema": "Ver esquema",
        "pregunta_ph": "Ex.: quanto faturamos por mês este ano, por filial?",
        "tu_pregunta": "Sua pergunta", "consultar": "Consultar",
        "ejemplos": "Exemplos", "generando": "Gerando SQL com IA e validando contra seu esquema…",
        "tablas_rag": "Tabelas relevantes detectadas", "sql_gen": "SQL gerado",
        "validado": "SQL validado contra o esquema real (sem nomes inventados)",
        "confianza": "Confiança", "supuestos": "Suposições do modelo",
        "resultado": "Resultado", "filas": "Linhas", "columnas": "Colunas",
        "tabla": "Tabela", "grafico": "Gráfico", "analisis": "Análise",
        "exportar": "Exportar", "guardar": "Salvar consulta",
        "nombre_consulta": "Nome da consulta", "guardada": "Consulta salva",
        "biblioteca": "Consultas salvas", "ejecutar": "Executar",
        "borrar": "Excluir", "sin_guardadas": "Nenhuma consulta salva ainda.",
        "sp": "Gerar stored procedure", "sp_nombre": "Nome do procedure",
        "optimizar": "Otimizar SQL (CTE)", "falta_key": "Configure o provedor de IA na barra lateral.",
        "falta_bd": "Conecte um banco de dados na barra lateral.",
        "historial": "Histórico", "descargar": "Baixar",
        "err_valid": "A validação encontrou problemas:", "advertencias": "Avisos",
        "sin_grafico": "Sem gráfico automático para este formato de dados.",
        "demo_hint": "Sem banco próprio? Use a demo: motor SQLite, caminho cartera_demo.db (gere com: python generar_db_demo.py).",
        "creditos_activos": "✓ Créditos ativos — {n} incluídos ({plan})",
        "creditos_licencia": "Licença de {email} · vence {vence}",
        "creditos_falta": "licencia_mvsql.json não encontrado nesta pasta. Este provedor só funciona no zip comprado com créditos embutidos.",
        "creditos_comprar": "[Comprar créditos]({url})",
        "fmt_titulo": "Formato de números", "fmt_dec": "Decimais",
        "fmt_miles": "Separador de milhares", "fmt_estilo": "Estilo",
        "fmt_pct_dec": "Decimais em porcentagens", "fmt_moneda": "Moeda",
        "fmt_sin_moneda": "(sem moeda)",
        "fmt_moneda_todas": "Aplicar moeda a todas as colunas numéricas",
        "fmt_hint": "Aplica-se a tabelas, gráficos e à resposta da IA.",
        "tipo_grafico": "Tipo de gráfico", "eje_x": "Eixo X", "eje_y": "Eixo Y",
        "g_auto": "✨ Automático (conforme os dados)", "g_barras": "Barras",
        "g_barras_h": "Barras horizontais", "g_linea": "Linha", "g_area": "Área",
        "g_torta": "Pizza", "g_dispersion": "Dispersão", "g_histo": "Histograma",
        "archivo": "📄 Arquivo (CSV / Excel / Parquet)",
        "subir_archivo": "Envie seu arquivo",
        "archivo_hint": "O arquivo vira uma base consultável na hora e fica em cache: a próxima carga é imediata. Excel: cada planilha vira uma tabela.",
        "archivo_falta": "Envie um arquivo primeiro.",
        "explorar": "Explorar", "eda_fuente": "Analisar",
        "eda_resultado": "O resultado atual",
        "eda_corr": "Correlação entre variáveis",
        "eda_infl": "Influência de variáveis", "eda_objetivo": "Variável alvo",
        "eda_infl_hint": "Importância calculada com Random Forest sobre uma amostra (até 5.000 linhas): quanto cada variável ajuda a prever a variável alvo.",
        "eda_pocas": "São necessárias pelo menos 2 colunas numéricas com variação para esta análise.",
        "eda_shap_hint": "Valores SHAP sobre Random Forest (amostra de até 1.500 linhas): o comprimento da barra é o quanto influencia; ▲ verde = aumentar essa variável aumenta {objetivo}; ▼ vermelho = a reduz.",
        "eda_shap_falta": "Instale o pacote 'shap' (pip install shap) para ver também a direção do efeito.",
    },
}

EJEMPLOS = {
    "es": ["¿Cuánto cobramos por mes en 2026?",
           "Top 10 clientes con más deuda en estado jurídico",
           "Contactabilidad por gestor (% de contactos exitosos)",
           "¿Cuántas operaciones por canal y su monto promedio?"],
    "en": ["Monthly collections in 2026?",
           "Top 10 clients with highest debt in legal status",
           "Contact rate by agent (% successful contacts)",
           "Operations per channel and average amount?"],
    "pt": ["Quanto cobramos por mês em 2026?",
           "Top 10 clientes com maior dívida em status jurídico",
           "Taxa de contato por gestor (% de contatos bem-sucedidos)",
           "Operações por canal e valor médio?"],
}

# ──────────────────────────────────────────────────────────────
# CONFIG DE PÁGINA + ESTILO
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="MV SQL NLP", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
  .stApp { background: linear-gradient(180deg,#0b1220 0%,#0f172a 100%); color:#e2e8f0; }
  section[data-testid="stSidebar"] { background:#0b1220; border-right:1px solid #1e293b; }
  h1,h2,h3,h4 { color:#f1f5f9 !important; }
  .mv-logo { font-size:2rem; font-weight:800;
    background:linear-gradient(90deg,#38bdf8,#818cf8,#c084fc);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .mv-badge { display:inline-block; background:#1e293b; color:#94a3b8;
    padding:.15rem .6rem; border-radius:99px; font-size:.72rem; margin-right:.3rem;
    border:1px solid #334155; }
  .stButton>button {
    background:linear-gradient(90deg,#2563eb,#7c3aed); color:#fff; border:none;
    border-radius:10px; padding:.55rem 1.4rem; font-weight:600; }
  .stButton>button:hover { filter:brightness(1.15); }
  div[data-testid="stMetricValue"] { color:#38bdf8; }
  .stTextInput input, .stSelectbox div, .stNumberInput input {
    background:#0b1220 !important; color:#e2e8f0 !important;
    border-radius:8px !important; }
  .conf-box { border:1px solid #334155; border-radius:12px; padding:.8rem 1rem;
    background:#0b1220; }
  .conf-bar-bg { background:#1e293b; border-radius:99px; height:10px; position:relative; }
  .conf-bar { background:linear-gradient(90deg,#22c55e,#38bdf8); border-radius:99px;
    height:10px; }
  .conf-interval { position:absolute; top:-3px; height:16px;
    border-left:2px solid #f8fafc55; border-right:2px solid #f8fafc55; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# ESTADO
# ──────────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("lang", "es")
ss.setdefault("motor", None)          # MotorMVSQL
ss.setdefault("historial", [])
ss.setdefault("pregunta_precargada", "")
ss.setdefault("resultado", None)


# ──────────────────────────────────────────────────────────────
# FORMATO DE NÚMEROS (decimales, miles, %, moneda) — elegido por el usuario
# ──────────────────────────────────────────────────────────────
MONEDAS = ["", "$U", "US$", "AR$", "R$", "€", "MX$", "CL$", "S/", "£"]
MONEDA_NOMBRE = {
    "$U": "pesos uruguayos (UYU)", "US$": "dólares (USD)",
    "AR$": "pesos argentinos (ARS)", "R$": "reales (BRL)", "€": "euros (EUR)",
    "MX$": "pesos mexicanos (MXN)", "CL$": "pesos chilenos (CLP)",
    "S/": "soles (PEN)", "£": "libras (GBP)",
}
_KEYS_MONEDA = ("monto", "importe", "deuda", "saldo", "total", "precio", "pago",
                "capital", "interes", "facturado", "facturacion", "cobrado",
                "venta", "amount", "revenue", "cost", "price", "value", "valor")
_KEYS_PCT = ("%", "pct", "porcentaje", "porcentagem", "percent", "tasa", "taxa",
             "rate", "contactabilidad", "ratio")


def _prefs():
    return dict(dec=int(ss.get("fmt_dec", 2)), miles=bool(ss.get("fmt_miles", True)),
                estilo=ss.get("fmt_estilo", "1.234,56"),
                pct_dec=int(ss.get("fmt_pct_dec", 1)),
                moneda=ss.get("fmt_moneda", ""),
                moneda_todas=bool(ss.get("fmt_moneda_todas", False)))


def fmt_numero(v, dec=None, pct=False, moneda=False, p=None):
    """Formatea un número según las preferencias del usuario."""
    p = p or _prefs()
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    dec = p["pct_dec"] if pct else (p["dec"] if dec is None else dec)
    try:
        s = f"{float(v):,.{dec}f}" if p["miles"] else f"{float(v):.{dec}f}"
    except (TypeError, ValueError):
        return str(v)
    if p["estilo"] == "1.234,56":
        s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    if pct:
        s += " %"
    if moneda and p["moneda"]:
        s = f"{p['moneda']} {s}"
    return s


def _tipo_columna(nombre, p):
    """'pct' / 'moneda' / 'num' según el nombre de la columna y las prefs."""
    n = str(nombre).lower()
    if any(k in n for k in _KEYS_PCT):
        return "pct"
    if p["moneda"] and (p["moneda_todas"] or any(k in n for k in _KEYS_MONEDA)):
        return "moneda"
    return "num"


def estilizar_df(df):
    """Devuelve un Styler con los números formateados para mostrar en tabla."""
    p = _prefs()
    fmts = {}
    for c in df.select_dtypes(include="number").columns:
        tipo = _tipo_columna(c, p)
        es_int = pd.api.types.is_integer_dtype(df[c])
        dec = 0 if (es_int and tipo == "num") else None
        fmts[c] = (lambda v, tipo=tipo, dec=dec, p=p:
                   fmt_numero(v, dec=dec, pct=(tipo == "pct"),
                              moneda=(tipo == "moneda"), p=p))
    try:
        return df.style.format(fmts)
    except Exception:
        return df


def contexto_formato():
    """Preferencias de formato que se pasan a la IA junto con la pregunta."""
    p = _prefs()
    partes = [f"redondear a {p['dec']} decimales"]
    if p["moneda"]:
        partes.append(f"los montos son en {MONEDA_NOMBRE.get(p['moneda'], p['moneda'])} "
                      f"— mencionar la moneda en el análisis")
    return "; ".join(partes)


# ──────────────────────────────────────────────────────────────
# GRÁFICOS — ejes con etiqueta, valores formateados sin solaparse,
# tipo acorde a los datos y elegible por el usuario
# ──────────────────────────────────────────────────────────────
PALETA = ["#38bdf8", "#818cf8", "#c084fc", "#f472b6", "#34d399",
          "#fbbf24", "#f87171", "#22d3ee"]


def _titulo_eje(col):
    return str(col).replace("_", " ").strip().capitalize()


def _cols_de(df):
    nums = df.select_dtypes(include="number").columns.tolist()
    fechas = [c for c in df.columns
              if pd.api.types.is_datetime64_any_dtype(df[c])
              or any(k in str(c).lower() for k in
                     ("fecha", "mes", "periodo", "dia", "anio", "año", "date",
                      "month", "data", "semana", "week"))]
    cats = [c for c in df.columns if c not in nums and c not in fechas]
    return nums, cats, fechas


def _aplicar_tema(fig, p, x=None, y=None, y_es_moneda=False, y_es_pct=False):
    dec = p["pct_dec"] if y_es_pct else p["dec"]
    fig.update_layout(
        plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e2e8f0",
        font_family="Inter, system-ui, sans-serif",
        separators=",." if p["estilo"] == "1.234,56" else ".,",
        # margen generoso arriba/derecha: las etiquetas de valores usan
        # cliponaxis=False y sin esto se cortan contra el borde del lienzo
        margin=dict(t=56, r=70, b=52, l=64),
        hoverlabel=dict(bgcolor="#1e293b", font_color="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        legend_title_text="",
        uniformtext_minsize=9, uniformtext_mode="hide",
        xaxis_title=_titulo_eje(x) if x else None,
        yaxis_title=_titulo_eje(y) if y else None,
    )
    tickfmt = f",.{dec}f" if p["miles"] else f".{dec}f"
    fig.update_yaxes(gridcolor="#1e293b", zerolinecolor="#334155",
                     tickformat=tickfmt, automargin=True,
                     tickprefix=f"{p['moneda']} " if (y_es_moneda and p["moneda"]) else None,
                     ticksuffix=" %" if y_es_pct else None)
    fig.update_xaxes(gridcolor="#1e293b", automargin=True)
    return fig


def graficar(df, tipo="auto", x=None, y=None):
    """Genera el gráfico. tipo: auto/barras/barras_h/linea/area/torta/dispersion/histo."""
    if df.empty or len(df) > 3000:
        return None
    p = _prefs()
    nums, cats, fechas = _cols_de(df)
    dfx = df.copy()

    def _misma_escala(cols):
        """Series con magnitudes MUY distintas en un mismo eje se aplastan:
        conservar solo las comparables con la primera."""
        if len(cols) <= 1:
            return cols
        base = abs(dfx[cols[0]].abs().max()) or 1
        return [c for c in cols
                if base / 50 <= (abs(dfx[c].abs().max()) or 1) <= base * 50]

    # elección automática de tipo y ejes
    if tipo == "auto":
        if fechas and nums:
            tipo, x, y = "linea", fechas[0], _misma_escala(nums[:4])
        elif cats and nums and len(dfx) <= 60:
            # nombres largos o muchas categorías → horizontal (no se solapan)
            etiquetas = dfx[cats[0]].astype(str)
            tipo = ("barras_h" if (etiquetas.str.len().max() > 12 or len(dfx) > 12)
                    else "barras")
            x, y = cats[0], _misma_escala(nums[:2])
        elif len(nums) >= 2:
            tipo, x, y = "dispersion", nums[0], [nums[1]]
        elif cats and dfx[cats[0]].nunique() <= 10:
            tipo, x, y = "torta", cats[0], None
        elif len(nums) == 1:
            tipo, x, y = "histo", nums[0], None
        else:
            return None
    if isinstance(y, str):
        y = [y]
    y = [c for c in (y or []) if c in dfx.columns] or (nums[:1] if nums else None)

    y0 = y[0] if y else None
    tipo_y = _tipo_columna(y0, p) if y0 else "num"
    es_moneda, es_pct = tipo_y == "moneda", tipo_y == "pct"
    dec = p["pct_dec"] if es_pct else p["dec"]
    vfmt = (f",.{dec}f" if p["miles"] else f".{dec}f")
    pref = f"{p['moneda']} " if (es_moneda and p["moneda"]) else ""
    suf = " %" if es_pct else ""

    try:
        if tipo == "linea" or tipo == "area":
            if not (x and y):
                return None
            dfx = dfx.sort_values(x)
            fn = px.area if tipo == "area" else px.line
            fig = fn(dfx, x=x, y=y, markers=True, color_discrete_sequence=PALETA)
            if len(dfx) <= 15 and len(y) == 1:      # etiquetas solo si no se amontonan
                fig.update_traces(texttemplate="%{y:" + vfmt + "}",
                                  textposition="top center", cliponaxis=False,
                                  mode="lines+markers+text")
            fig = _aplicar_tema(fig, p, x, y0 if len(y) == 1 else None, es_moneda, es_pct)
            fig.update_layout(showlegend=len(y) > 1)

        elif tipo in ("barras", "barras_h"):
            if not (x and y):
                return None
            dfx = dfx.sort_values(y0, ascending=(tipo == "barras_h"))
            if tipo == "barras_h":
                fig = px.bar(dfx, y=x, x=y, orientation="h", barmode="group",
                             color_discrete_sequence=PALETA)
                if len(dfx) <= 30:
                    fig.update_traces(texttemplate="%{x:" + vfmt + "}",
                                      textposition="outside", cliponaxis=False)
                fig = _aplicar_tema(fig, p, y0 if len(y) == 1 else None, x)
                tickfmt = f",.{dec}f" if p["miles"] else f".{dec}f"
                fig.update_xaxes(tickformat=tickfmt, tickprefix=pref or None,
                                 ticksuffix=suf or None)
                fig.update_yaxes(tickformat=None, tickprefix=None, ticksuffix=None,
                                 automargin=True)
                fig.update_layout(height=max(360, 32 * len(dfx) + 120),
                                  yaxis_title=_titulo_eje(x),
                                  xaxis_title=_titulo_eje(y0) if len(y) == 1 else None)
            else:
                fig = px.bar(dfx, x=x, y=y, barmode="group",
                             color_discrete_sequence=PALETA)
                if len(dfx) <= 30:
                    fig.update_traces(texttemplate="%{y:" + vfmt + "}",
                                      textposition="outside", cliponaxis=False)
                fig = _aplicar_tema(fig, p, x, y0 if len(y) == 1 else None,
                                    es_moneda, es_pct)
                fig.update_layout(showlegend=len(y) > 1)
                if dfx[x].astype(str).str.len().max() > 8 or len(dfx) > 8:
                    fig.update_xaxes(tickangle=-30)   # que no se pisen las etiquetas

        elif tipo == "dispersion":
            if not (x and y):
                return None
            fig = px.scatter(dfx, x=x, y=y0, color=cats[0] if cats else None,
                             color_discrete_sequence=PALETA)
            fig = _aplicar_tema(fig, p, x, y0, es_moneda, es_pct)

        elif tipo == "torta":
            col = x or (cats[0] if cats else None)
            if col is None:
                return None
            if y and y0 in nums:
                vc = dfx.groupby(col, as_index=False)[y0].sum().nlargest(12, y0)
                names, values = col, y0
            else:
                vc = dfx[col].value_counts().reset_index().head(12)
                vc.columns = [col, "n"]
                names, values = col, "n"
            fig = px.pie(vc, names=names, values=values, hole=0.35,
                         color_discrete_sequence=PALETA)
            fig.update_traces(textinfo="label+percent",
                              texttemplate="%{label}<br>%{percent:.1%}")
            fig = _aplicar_tema(fig, p)

        elif tipo == "histo":
            col = x or (nums[0] if nums else None)
            if col is None:
                return None
            fig = px.histogram(dfx, x=col, color_discrete_sequence=PALETA)
            fig = _aplicar_tema(fig, p, col, None)
            fig.update_layout(yaxis_title="Frecuencia")

        else:
            return None

        # hover con el formato elegido
        if tipo not in ("torta", "histo"):
            fig.update_traces(hovertemplate=None)
        return fig
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# EXPLORAR (EDA) — correlación entre variables e influencia de unas
# sobre otras (Random Forest), sobre el resultado o una tabla completa
# ──────────────────────────────────────────────────────────────
def _sin_ids(df_e):
    """Columnas *_id / id no aportan al análisis y dominan los rankings."""
    fuera = [c for c in df_e.columns
             if str(c).lower() == "id" or str(c).lower().endswith("_id")]
    return df_e.drop(columns=fuera) if fuera else df_e


def eda_correlacion(df_e):
    """Mapa de calor de correlaciones entre las columnas numéricas."""
    nums = _sin_ids(df_e).select_dtypes(include="number")
    nums = nums.loc[:, nums.nunique() > 1]
    if nums.shape[1] < 2:
        return None
    corr = nums.corr(numeric_only=True).round(2)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1, aspect="auto")
    fig.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                      font_color="#e2e8f0", margin=dict(t=30, r=30, b=30, l=30),
                      coloraxis_colorbar=dict(title=""))
    fig.update_xaxes(tickangle=-30)
    return fig


def eda_influencia(df_e, objetivo, t):
    """Qué variables influyen sobre `objetivo` y en qué dirección.

    Con `shap` instalado usa valores SHAP sobre un Random Forest (magnitud
    + dirección del efecto); si no está, cae a la importancia del bosque
    (solo magnitud). Devuelve (figura, usa_shap).
    """
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

    d = _sin_ids(df_e).dropna(subset=[objetivo])
    if len(d) < 20:
        return None, False
    y = d[objetivo]
    X = d.drop(columns=[objetivo])
    Xe = pd.DataFrame(index=d.index)
    for c in X.columns:
        col = X[c]
        if pd.api.types.is_numeric_dtype(col):
            Xe[c] = col.fillna(col.median())
        elif pd.api.types.is_datetime64_any_dtype(col):
            Xe[c] = col.astype("int64")
        elif col.nunique() <= 50:
            Xe[c] = pd.factorize(col.astype(str))[0]
    if Xe.shape[1] < 1:
        return None, False
    es_regresion = pd.api.types.is_numeric_dtype(y) and y.nunique() > 10
    if es_regresion:
        modelo = RandomForestRegressor(n_estimators=60, max_depth=8,
                                       random_state=0, n_jobs=-1)
        y_fit = y.astype(float)
    else:
        modelo = RandomForestClassifier(n_estimators=60, max_depth=8,
                                        random_state=0, n_jobs=-1)
        y_fit = pd.factorize(y.astype(str))[0]
    try:
        modelo.fit(Xe, y_fit)
    except Exception:
        return None, False

    # ── SHAP: magnitud + dirección del efecto ──
    usa_shap = False
    try:
        import shap

        Xs = Xe.sample(min(len(Xe), 1500), random_state=0)
        sv = shap.TreeExplainer(modelo).shap_values(Xs)
        if isinstance(sv, list):          # clasificador (versiones viejas)
            sv = sv[-1]
        if getattr(sv, "ndim", 2) == 3:   # clasificador (versiones nuevas)
            sv = sv[:, :, -1]
        mag = np.abs(sv).mean(axis=0)
        if mag.sum() <= 0:
            raise ValueError("SHAP sin señal")
        pesos = pd.Series(mag / mag.sum(), index=Xe.columns)
        direcciones = {}
        for j, c in enumerate(Xe.columns):
            with np.errstate(invalid="ignore"):
                r = np.corrcoef(Xs[c], sv[:, j])[0, 1]
            direcciones[c] = 0.0 if pd.isna(r) else r
        usa_shap = True
    except Exception:
        pesos = pd.Series(modelo.feature_importances_, index=Xe.columns)
        direcciones = {c: 0.0 for c in Xe.columns}

    pesos = pesos.sort_values().tail(12)
    colores, textos = [], []
    for c, v in pesos.items():
        if usa_shap and direcciones[c] < -0.05:
            colores.append("#f87171")             # al subir la variable, BAJA
            textos.append(f"{v:.0%} ▼")
        elif usa_shap and direcciones[c] > 0.05:
            colores.append("#34d399")             # al subir la variable, SUBE
            textos.append(f"{v:.0%} ▲")
        else:
            colores.append("#38bdf8")
            textos.append(f"{v:.0%}")
    fig = px.bar(x=pesos.values, y=[_titulo_eje(c) for c in pesos.index],
                 orientation="h")
    fig.update_traces(marker_color=colores, text=textos,
                      textposition="outside", cliponaxis=False)
    fig.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                      font_color="#e2e8f0", margin=dict(t=30, r=60, b=40, l=30),
                      xaxis_title=None, yaxis_title=None, showlegend=False,
                      height=max(300, 34 * len(pesos) + 90))
    fig.update_xaxes(tickformat=".0%", gridcolor="#1e293b")
    return fig, usa_shap


# ──────────────────────────────────────────────────────────────
# MODO ARCHIVO — CSV/Excel/Parquet/JSON a base consultable, con caché
# (la primera carga convierte; las siguientes son instantáneas)
# ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def archivo_a_sqlite(nombre, contenido: bytes) -> str:
    import hashlib
    import io
    import re as _re
    import sqlite3
    import tempfile

    h = hashlib.sha1(contenido).hexdigest()[:12]
    ruta = os.path.join(tempfile.gettempdir(), f"mvsql_archivo_{h}.db")
    if os.path.exists(ruta):
        return ruta          # ya convertido en una sesión anterior

    ext = nombre.lower().rsplit(".", 1)[-1]
    buf = io.BytesIO(contenido)
    if ext == "csv":
        try:
            tablas = {"datos": pd.read_csv(io.BytesIO(contenido), engine="pyarrow")}
        except Exception:      # pyarrow no instalado o CSV raro → autodetectar separador
            tablas = {"datos": pd.read_csv(buf, sep=None, engine="python")}
    elif ext in ("xlsx", "xls"):
        hojas = pd.read_excel(buf, sheet_name=None)
        tablas = {(_re.sub(r"\W+", "_", str(k)).strip("_").lower() or f"hoja{i}"): v
                  for i, (k, v) in enumerate(hojas.items(), 1)}
    elif ext == "parquet":
        tablas = {"datos": pd.read_parquet(buf)}
    else:                      # json
        tablas = {"datos": pd.read_json(buf)}

    tmp = ruta + ".tmp"
    con = sqlite3.connect(tmp)
    try:
        for tabla, df_t in tablas.items():
            df_t.columns = [_re.sub(r"\W+", "_", str(c)).strip("_") or f"col{i}"
                            for i, c in enumerate(df_t.columns)]
            df_t.to_sql(tabla, con, index=False, if_exists="replace")
        con.commit()
    finally:
        con.close()
    os.replace(tmp, ruta)
    return ruta


def barra_confianza(conf, t):
    p, (lo, hi) = conf["puntaje"], conf["intervalo"]
    comp = conf["componentes"]
    st.markdown(f"""
<div class="conf-box">
  <b>{t['confianza']}: {p}% &nbsp;<span style="color:#94a3b8">(±{conf['margen']} → intervalo {lo}–{hi}%)</span></b>
  <div class="conf-bar-bg" style="margin-top:.5rem">
    <div class="conf-bar" style="width:{p}%"></div>
    <div class="conf-interval" style="left:{lo}%; width:{hi - lo}%"></div>
  </div>
  <div style="color:#94a3b8; font-size:.75rem; margin-top:.4rem">
    modelo {comp['modelo']} · RAG {comp['rag']} · validación {comp['validacion']}
  </div>
</div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# SIDEBAR — idioma, IA, base de datos
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="mv-logo">⚡ MV SQL NLP</div>', unsafe_allow_html=True)

    ss.lang = st.selectbox("🌐", ["es", "en", "pt"],
                           index=["es", "en", "pt"].index(ss.lang),
                           format_func=lambda x: {"es": "Español", "en": "English",
                                                  "pt": "Português"}[x])
    t = T[ss.lang]

    with st.expander(f"🔢 {t['fmt_titulo']}"):
        c1, c2 = st.columns(2)
        c1.number_input(t["fmt_dec"], 0, 6, 2, key="fmt_dec")
        c2.number_input(t["fmt_pct_dec"], 0, 4, 1, key="fmt_pct_dec")
        st.checkbox(t["fmt_miles"], value=True, key="fmt_miles")
        st.radio(t["fmt_estilo"], ["1.234,56", "1,234.56"], horizontal=True,
                 key="fmt_estilo")
        st.selectbox(t["fmt_moneda"], MONEDAS, key="fmt_moneda",
                     format_func=lambda m: t["fmt_sin_moneda"] if m == "" else
                     f"{m} — {MONEDA_NOMBRE.get(m, '')}")
        if ss.get("fmt_moneda"):
            st.checkbox(t["fmt_moneda_todas"], key="fmt_moneda_todas")
        st.caption(t["fmt_hint"])

    st.divider()
    st.subheader(f"🤖 {t['ia']}")
    prov_keys = list(PROVEEDORES.keys())
    proveedor = st.selectbox(t["ia"], prov_keys, label_visibility="collapsed",
                             format_func=lambda k: PROVEEDORES[k]["nombre"])
    info_prov = PROVEEDORES[proveedor]
    modelo, base_url, api_key = "", None, ""

    if proveedor == "mvsql_creditos":
        licencia = cargar_licencia_creditos()
        if licencia:
            st.success(t["creditos_activos"].format(
                n=licencia.get("creditos", "?"), plan=licencia.get("plan", "")))
            st.caption(t["creditos_licencia"].format(
                email=licencia.get("email", ""), vence=licencia.get("vence", "")[:10]))
        else:
            st.error(t["creditos_falta"])
            st.caption(t["creditos_comprar"].format(url=info_prov["url_keys"]))
    else:
        if info_prov["modelos"]:
            modelo = st.selectbox(t["modelo"], info_prov["modelos"],
                                  index=info_prov["modelos"].index(info_prov["modelo_default"]))
        else:
            modelo = st.text_input(t["modelo"], placeholder="gpt-4o-mini")

        if proveedor in ("custom", "ollama"):
            base_url = st.text_input("Base URL",
                                     value="http://localhost:11434" if proveedor == "ollama" else "",
                                     placeholder="https://api.miproveedor.com/v1")

        if info_prov["necesita_key"]:
            api_key = st.text_input(t["apikey"], type="password",
                                    value=os.environ.get(f"{proveedor.upper()}_API_KEY",
                                                         os.environ.get("ANTHROPIC_API_KEY", "")
                                                         if proveedor == "anthropic" else ""))
            if info_prov["url_keys"]:
                st.caption(f"[Obtener API key]({info_prov['url_keys']})")

    if st.button(f"🔌 {t['probar']}", use_container_width=True):
        ok, msg = probar_conexion(proveedor, api_key, modelo, base_url)
        (st.success if ok else st.error)(msg)

    ia_cfg = {"proveedor": proveedor, "api_key": api_key,
              "modelo": modelo, "base_url": base_url}

    st.divider()
    st.subheader(f"🗄️ {t['bd']}")
    motor_bd = st.selectbox(t["motor_bd"], ["archivo"] + list(MOTORES.keys()),
                            format_func=lambda k: t["archivo"] if k == "archivo"
                            else MOTORES[k]["nombre"])

    if motor_bd == "archivo":
        archivo_subido = st.file_uploader(
            t["subir_archivo"], type=["csv", "xlsx", "xls", "parquet", "json"])
        st.caption(t["archivo_hint"])
        params = None
    elif motor_bd == "sqlite":
        ruta = st.text_input("Archivo .db", value="cartera_demo.db")
        params = dict(ruta=ruta)
    else:
        c1, c2 = st.columns([3, 1])
        servidor = c1.text_input("Servidor / host")
        puerto = c2.text_input("Puerto", value="")
        base = st.text_input("Base")
        usuario = st.text_input("Usuario")
        password = st.text_input("Password", type="password")
        params = dict(servidor=servidor, puerto=puerto or None, base=base,
                      usuario=usuario, password=password)

    if st.button(f"🔗 {t['conectar']}", use_container_width=True, type="primary"):
        try:
            with st.spinner("…"):
                if motor_bd == "archivo":
                    if archivo_subido is None:
                        st.error(t["archivo_falta"])
                        st.stop()
                    ruta_db = archivo_a_sqlite(archivo_subido.name,
                                               archivo_subido.getvalue())
                    cx = ConexionBD("sqlite", ruta=ruta_db).conectar()
                else:
                    cx = ConexionBD(motor_bd, **params).conectar()
                ss.motor = MotorMVSQL(cx, ia_cfg)
            st.success(f"✓ {len(ss.motor.catalogo['tablas'])} {t['tablas_ok']}")
        except Exception as e:
            st.error(str(e))

    if ss.motor:
        ss.motor.ia = ia_cfg  # refrescar credenciales sin reconectar
        st.success(f"✓ {len(ss.motor.catalogo['tablas'])} {t['tablas_ok']}")
        with st.expander(f"📚 {t['ver_esquema']}"):
            for tb, info in ss.motor.catalogo["tablas"].items():
                n = info.get("n_filas")
                st.markdown(f"**{tb}**" + (f" · {n:,} filas" if n else ""))
                st.caption(", ".join(c["columna"] for c in info["columnas"]))
    else:
        st.info(t["demo_hint"])

    st.divider()
    # ── Biblioteca de consultas guardadas ──
    st.subheader(f"⭐ {t['biblioteca']}")
    items = guardadas.listar()
    if not items:
        st.caption(t["sin_guardadas"])
    for it in items:
        with st.expander(f"📌 {it['nombre']}"):
            st.caption(it.get("pregunta", ""))
            st.code(it["sql"], language="sql")
            c1, c2 = st.columns(2)
            if c1.button(f"▶ {t['ejecutar']}", key=f"run_{it['nombre']}"):
                ss.pregunta_precargada = it.get("pregunta", "")
                ss.sql_directo = it["sql"]
            if c2.button(f"🗑 {t['borrar']}", key=f"del_{it['nombre']}"):
                guardadas.eliminar(it["nombre"])
                st.rerun()


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
st.markdown(f'<div class="mv-logo" style="font-size:2.6rem">⚡ {t["titulo"]}</div>',
            unsafe_allow_html=True)
st.markdown(f"<p style='color:#94a3b8; max-width:60rem'>{t['sub']}</p>",
            unsafe_allow_html=True)
st.markdown('<span class="mv-badge">SELECT-only</span>'
            '<span class="mv-badge">RAG local</span>'
            '<span class="mv-badge">CTE optimizado</span>'
            '<span class="mv-badge">Multi-IA</span>'
            '<span class="mv-badge">ES · EN · PT</span>', unsafe_allow_html=True)
st.write("")

st.markdown(f"**{t['ejemplos']}:**")
cols_ej = st.columns(4)
for i, ej in enumerate(EJEMPLOS[ss.lang]):
    if cols_ej[i % 4].button(ej, key=f"ej{i}", use_container_width=True):
        ss.pregunta_precargada = ej

pregunta = st.text_input(t["tu_pregunta"], value=ss.pregunta_precargada,
                         placeholder=t["pregunta_ph"])
ejecutar = st.button(f"⚡ {t['consultar']}", type="primary")

if ejecutar and pregunta:
    if ss.motor is None:
        st.error(t["falta_bd"])
        st.stop()
    if PROVEEDORES[ia_cfg["proveedor"]]["necesita_key"] and not ia_cfg["api_key"]:
        st.error(t["falta_key"])
        st.stop()
    with st.spinner(t["generando"]):
        try:
            ss.resultado = ss.motor.responder(pregunta, contexto=contexto_formato())
            ss.historial.insert(0, {"pregunta": pregunta,
                                    "sql": ss.resultado["sql"]})
        except Exception as e:
            st.error(str(e))
            st.stop()
    ss.pregunta_precargada = ""

r = ss.resultado
if r:
    st.write("")
    st.markdown(f"##### 🎯 {t['tablas_rag']}")
    st.write(" · ".join(f"`{tb}`" for tb in r["tablas_recuperadas"]))

    c_sql, c_conf = st.columns([3, 2])
    with c_sql:
        st.markdown(f"##### 🧾 {t['sql_gen']}")
        st.code(r["sql"], language="sql")
        if r["valido"]:
            st.success(f"✓ {t['validado']}")
        else:
            st.error(t["err_valid"])
            for p in r["problemas"]:
                st.write(f"- {p}")
        if r["advertencias"]:
            with st.expander(f"⚠️ {t['advertencias']}"):
                for a in r["advertencias"]:
                    st.write(f"- {a}")
    with c_conf:
        st.markdown("##### 📐 " + t["confianza"])
        if r["confianza"]:
            barra_confianza(r["confianza"], t)
        if r["supuestos"] and r["supuestos"].lower() not in ("ninguno", "none", "nenhum"):
            st.caption(f"💭 {t['supuestos']}: {r['supuestos']}")

    if r["error"]:
        st.error(r["error"])

    if r["columnas"] and r["filas"] is not None:
        df = pd.DataFrame(r["filas"], columns=r["columnas"])
        for c in df.columns:
            if any(k in c.lower() for k in ("fecha", "date", "data")):
                try:
                    df[c] = pd.to_datetime(df[c])
                except (ValueError, TypeError):
                    pass

        st.markdown(f"##### 📊 {t['resultado']}")
        m1, m2, m3 = st.columns(3)
        m1.metric(t["filas"], fmt_numero(len(df), dec=0))
        m2.metric(t["columnas"], len(df.columns))
        nums = df.select_dtypes(include="number").columns.tolist()
        if nums:
            tipo_c = _tipo_columna(nums[0], _prefs())
            m3.metric(f"Σ {_titulo_eje(nums[0])}",
                      fmt_numero(df[nums[0]].sum(), pct=(tipo_c == "pct"),
                                 moneda=(tipo_c == "moneda")))

        tab1, tab2, tab3, tab5, tab4 = st.tabs([
            f"📋 {t['tabla']}", f"📈 {t['grafico']}", f"🧠 {t['analisis']}",
            f"🔍 {t['explorar']}", f"⬇️ {t['exportar']}"])
        with tab1:
            st.dataframe(estilizar_df(df), use_container_width=True, height=420)
        with tab2:
            TIPOS_G = {"auto": t["g_auto"], "barras": t["g_barras"],
                       "barras_h": t["g_barras_h"], "linea": t["g_linea"],
                       "area": t["g_area"], "torta": t["g_torta"],
                       "dispersion": t["g_dispersion"], "histo": t["g_histo"]}
            g1, g2, g3 = st.columns([2, 2, 2])
            tipo_g = g1.selectbox(t["tipo_grafico"], list(TIPOS_G.keys()),
                                  format_func=TIPOS_G.get, key="tipo_grafico")
            gx = gy = None
            if tipo_g != "auto":
                gx = g2.selectbox(t["eje_x"], list(df.columns), key="graf_x")
                if tipo_g not in ("torta", "histo"):
                    gy = g3.multiselect(t["eje_y"], nums,
                                        default=nums[:1], key="graf_y")
            fig = graficar(df, tipo=tipo_g, x=gx, y=gy)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(t["sin_grafico"])
        with tab3:
            st.write(r["explicacion"] or "—")
        with tab5:
            # EDA: sobre el resultado actual o sobre una tabla completa
            fuentes = [t["eda_resultado"]]
            if ss.motor:
                fuentes += list(ss.motor.catalogo["tablas"].keys())
            fuente = st.selectbox(t["eda_fuente"], fuentes, key="eda_fuente")
            if fuente == t["eda_resultado"]:
                df_eda = df
            else:
                try:
                    cols_e, filas_e, _ = ss.motor.cx.ejecutar(
                        f"SELECT * FROM {fuente}", limite=5000)
                    df_eda = pd.DataFrame(filas_e, columns=cols_e)
                except Exception as e:
                    st.error(str(e))
                    df_eda = df

            st.markdown(f"###### 🔗 {t['eda_corr']}")
            fig_corr = eda_correlacion(df_eda)
            if fig_corr:
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info(t["eda_pocas"])

            st.markdown(f"###### 🎯 {t['eda_infl']}")
            candidatas = [c for c in _sin_ids(df_eda).columns
                          if df_eda[c].nunique() > 1]
            if len(candidatas) >= 2:
                objetivo = st.selectbox(t["eda_objetivo"], candidatas,
                                        index=len(candidatas) - 1 if candidatas else 0,
                                        key="eda_objetivo")
                fig_infl, usa_shap = eda_influencia(df_eda, objetivo, t)
                if fig_infl:
                    st.plotly_chart(fig_infl, use_container_width=True)
                    if usa_shap:
                        st.caption(t["eda_shap_hint"].format(objetivo=objetivo))
                    else:
                        st.caption(f"{t['eda_infl_hint']} {t['eda_shap_falta']}")
                else:
                    st.info(t["eda_pocas"])
            else:
                st.info(t["eda_pocas"])
        with tab4:
            c1, c2, c3, c4 = st.columns(4)
            c1.download_button("Excel (.xlsx)",
                               a_excel(df, sql=r["sql_ejecutado"] or r["sql"]),
                               "mvsql_resultado.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
            c2.download_button("CSV", a_csv(df), "mvsql_resultado.csv", "text/csv",
                               use_container_width=True)
            c3.download_button("PDF", a_pdf(df, pregunta=r["pregunta"],
                                            sql=r["sql_ejecutado"] or r["sql"],
                                            explicacion=r["explicacion"] or ""),
                               "mvsql_resultado.pdf", "application/pdf",
                               use_container_width=True)
            c4.download_button("HTML", a_html(df), "mvsql_resultado.html", "text/html",
                               use_container_width=True)

        # ── acciones sobre la consulta ──
        st.divider()
        a1, a2, a3 = st.columns(3)
        with a1:
            with st.popover(f"⭐ {t['guardar']}"):
                nombre = st.text_input(t["nombre_consulta"],
                                       key="nombre_guardar")
                if st.button("OK", key="btn_guardar") and nombre:
                    guardadas.guardar(nombre, r["pregunta"], r["sql"],
                                      dialecto=ss.motor.cx.dialecto)
                    st.success(t["guardada"])
        with a2:
            with st.popover(f"🧱 {t['sp']}"):
                sp_nombre = st.text_input(t["sp_nombre"], value="sp_mvsql_reporte",
                                          key="sp_nombre")
                if st.button("OK", key="btn_sp"):
                    with st.spinner("…"):
                        codigo = ss.motor.generar_stored_procedure(r["sql"], sp_nombre)
                    st.code(codigo, language="sql")
        with a3:
            if st.button(f"🚀 {t['optimizar']}"):
                with st.spinner("…"):
                    st.code(ss.motor.optimizar_sql(r["sql"]), language="sql")

# historial
if ss.historial:
    with st.expander(f"🕘 {t['historial']} ({len(ss.historial)})"):
        for h in ss.historial[:20]:
            st.markdown(f"**{h['pregunta']}**")
            st.code(h["sql"], language="sql")

st.divider()
st.caption("MV SQL NLP · RAG local (tu esquema nunca sale sin tu permiso, los datos jamás) · "
           "solo SELECT · CTEs optimizados · mvsqlnlp.com")
