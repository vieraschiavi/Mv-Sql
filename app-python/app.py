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


def graficar_auto(df):
    if df.empty or len(df) > 500:
        return None
    cols_num = df.select_dtypes(include="number").columns.tolist()
    cols_cat = [c for c in df.columns if c not in cols_num]
    cols_fecha = [c for c in df.columns if any(k in c.lower() for k in
                  ("fecha", "mes", "periodo", "dia", "anio", "año", "date", "month", "data"))]
    tema = dict(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font_color="#e2e8f0")
    try:
        if cols_fecha and cols_num:
            fig = px.line(df.sort_values(cols_fecha[0]), x=cols_fecha[0], y=cols_num[0],
                          markers=True, color_discrete_sequence=["#38bdf8"])
        elif cols_cat and cols_num and len(df) <= 40:
            fig = px.bar(df.sort_values(cols_num[0], ascending=False),
                         x=cols_cat[0], y=cols_num[0],
                         color_discrete_sequence=["#818cf8"])
        elif len(cols_num) >= 2:
            fig = px.scatter(df, x=cols_num[0], y=cols_num[1],
                             color_discrete_sequence=["#c084fc"])
        elif cols_cat and df[cols_cat[0]].nunique() <= 10:
            vc = df[cols_cat[0]].value_counts().reset_index()
            vc.columns = [cols_cat[0], "n"]
            fig = px.pie(vc, names=cols_cat[0], values="n")
        else:
            return None
        fig.update_layout(**tema)
        return fig
    except Exception:
        return None


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
    motor_bd = st.selectbox(t["motor_bd"], list(MOTORES.keys()),
                            format_func=lambda k: MOTORES[k]["nombre"])

    if motor_bd == "sqlite":
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
            ss.resultado = ss.motor.responder(pregunta)
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
        m1.metric(t["filas"], f"{len(df):,}")
        m2.metric(t["columnas"], len(df.columns))
        nums = df.select_dtypes(include="number").columns.tolist()
        if nums:
            m3.metric(f"Σ {nums[0]}", f"{df[nums[0]].sum():,.0f}")

        tab1, tab2, tab3, tab4 = st.tabs([f"📋 {t['tabla']}", f"📈 {t['grafico']}",
                                          f"🧠 {t['analisis']}", f"⬇️ {t['exportar']}"])
        with tab1:
            st.dataframe(df, use_container_width=True, height=420)
        with tab2:
            fig = graficar_auto(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(t["sin_grafico"])
        with tab3:
            st.write(r["explicacion"] or "—")
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
