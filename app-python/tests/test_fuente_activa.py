# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_fuente_activa.py — la base del cliente reemplaza a la demo EN TODA la app
==================================================================
Pedido del cliente: «al elegir dataset por archivo o SQL debería aplicarse
a todas las pestañas y desaparecer los datos demo».

Lo que pasaba: la conexión cambiaba, pero cada sección guardaba sus
propios derivados (el último resultado, la frescura, el historial, las
tablas elegidas en el diagrama y en Explorar) y los ejemplos de
cobranzas quedaban fijos. Con su archivo cargado, el cliente seguía
viendo la base sintética.

Se prueba:
  1. Con fuente propia, CADA consumidor (consulta, cuadernos, frescura,
     diagrama, esquema, plan, Explorar, equipo, ejemplos) resuelve a ella.
  2. Volver a la demo (o cerrar sesión) trae la demo de vuelta.
  3. El catálogo de la demo nunca se filtra al del cliente.
  4. app.py no lee ni escribe la conexión por fuera del resolvedor.
  5. (si hay streamlit) la app real: conectar la base propia cambia el
     indicador y el esquema, y «Volver a la demo» la restituye.
"""
import os
import re
import sqlite3
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

import equipo            # noqa: E402
import esquema_visual    # noqa: E402
import frescura          # noqa: E402
import fuente            # noqa: E402
from conectores import ConexionBD   # noqa: E402
from motor import MotorMVSQL        # noqa: E402

pasadas = falladas = 0


def test(nombre):
    def deco(fn):
        global pasadas, falladas
        try:
            fn(); print(f"  ✓ {nombre}"); pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}"); falladas += 1
    return deco


# ── Dos bases sin ninguna tabla en común ─────────────────────────────
TMP = tempfile.mkdtemp(prefix="mvsql_fuente_")
DEMO_DB = os.path.join(TMP, "cartera_demo.db")
USER_DB = os.path.join(TMP, "mis_ventas.db")
TABLAS_DEMO = {"clientes", "cobranzas"}
TABLAS_USER = {"ventas", "productos"}


def _crear(ruta, ddl):
    con = sqlite3.connect(ruta)
    con.executescript(ddl)
    con.commit()
    con.close()


_crear(DEMO_DB, """
CREATE TABLE clientes (id INTEGER PRIMARY KEY, nombre TEXT, fecha_alta TEXT);
CREATE TABLE cobranzas (id INTEGER PRIMARY KEY, cliente_id INTEGER REFERENCES clientes(id),
                        monto REAL, fecha_carga TEXT);
INSERT INTO clientes VALUES (1, 'Demo SA', '2026-01-01');
INSERT INTO cobranzas VALUES (1, 1, 100.0, '2026-01-02');
""")
_crear(USER_DB, """
CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT);
CREATE TABLE ventas (id INTEGER PRIMARY KEY, producto_id INTEGER REFERENCES productos(id),
                     importe REAL, fecha_carga TEXT);
INSERT INTO productos VALUES (1, 'Mate');
INSERT INTO ventas VALUES (1, 1, 250.0, '2026-09-01'), (2, 1, 80.0, '2026-09-02');
""")

fuente.RUTA_DEMO = DEMO_DB
IA = {"proveedor": "anthropic", "api_key": "", "modelo": "", "base_url": None}


def fabricar(ruta):
    return MotorMVSQL(ConexionBD("sqlite", ruta=ruta).conectar(), IA)


def estado_con_demo():
    e = {}
    fuente.asegurar(e, fabricar)
    # Derivados «de la demo», como los deja un rato de uso.
    e["resultado"] = {"sql": "SELECT * FROM cobranzas", "tablas_recuperadas": ["cobranzas"]}
    e["frescura"] = [{"tabla": "cobranzas"}]
    e["historial"] = [{"pregunta": "¿Cuánto cobramos?", "sql": "SELECT 1"}]
    e["pregunta_precargada"] = "Top 10 clientes con más deuda"
    e["diag_tablas"] = ["clientes"]
    e["eda_fuente"] = "cobranzas"
    e["eq_tablas"] = ["clientes"]
    e["graf_x"] = "monto"
    return e


def pasar_a_usuario(e):
    fuente.usar_usuario(e, fabricar(USER_DB), "mis_ventas.db", "sqlite:mis_ventas.db")


def texto_de(obj):
    return repr(obj).lower()


print("\n== Arranque ==")


@test("sin fuente elegida, la app arranca con la demo")
def _():
    e = {}
    fuente.asegurar(e, fabricar)
    assert fuente.es_demo(e), fuente.activa(e)
    assert set(fuente.motor(e).catalogo["tablas"]) == TABLAS_DEMO


@test("sin la base demo en disco, arranca sin fuente (y sin error)")
def _():
    original = fuente.RUTA_DEMO
    fuente.RUTA_DEMO = os.path.join(TMP, "no_existe.db")
    try:
        e = {}
        fuente.asegurar(e, fabricar)
        assert fuente.motor(e) is None and fuente.activa(e) is None
    finally:
        fuente.RUTA_DEMO = original


print("\n== Con la fuente del cliente, TODO resuelve a ella ==")


@test("el motor activo es el del cliente y su catálogo no trae NADA de la demo")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    m = fuente.motor(e)
    assert fuente.activa(e)["tipo"] == fuente.USUARIO
    assert set(m.catalogo["tablas"]) == TABLAS_USER, m.catalogo["tablas"].keys()
    for t in TABLAS_DEMO:
        assert t not in texto_de(m.catalogo), f"'{t}' de la demo se filtró al catálogo"
        assert t not in texto_de(m.fichas), f"'{t}' de la demo quedó en el RAG"


@test("los derivados de la demo se borran al cambiar de fuente")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    assert e["resultado"] is None
    assert e["historial"] == [] and e["pregunta_precargada"] == ""
    for clave in ("frescura", "diag_tablas", "eda_fuente", "eq_tablas", "graf_x"):
        assert clave not in e, f"'{clave}' sobrevivió con datos de la demo"


@test("la conexión de la demo se cierra (no queda colgada)")
def _():
    e = estado_con_demo()
    cx_demo = fuente.motor(e).cx
    pasar_a_usuario(e)
    assert cx_demo._con is None, "la conexión a la demo sigue abierta"


@test("consulta / cuadernos / Explorar: ejecutan contra la base del cliente")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    cx = fuente.motor(e).cx
    _c, filas, _ = cx.ejecutar("SELECT SUM(importe) FROM ventas")
    assert filas[0][0] == 330.0
    try:
        cx.ejecutar("SELECT monto FROM cobranzas")
        raise AssertionError("la tabla de la demo sigue alcanzable")
    except sqlite3.OperationalError:
        pass


@test("frescura: solo tablas del cliente")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    m = fuente.motor(e)
    filas = frescura.analizar(m.cx, m.catalogo)
    assert {f["tabla"] for f in filas} == TABLAS_USER, filas


@test("diagrama de relaciones y esquema: solo tablas del cliente")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    cat = fuente.motor(e).catalogo
    dot = esquema_visual.diagrama_dot(cat).lower()
    assert "ventas" in dot and "productos" in dot
    for t in TABLAS_DEMO:
        assert t not in dot, f"'{t}' de la demo en el diagrama"
    rel = texto_de(esquema_visual.resumen_relaciones(cat))
    assert "clientes" not in rel and "cobranzas" not in rel


@test("plan de ejecución: corre sobre la conexión del cliente")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    filas, _h = esquema_visual.plan_de_ejecucion(fuente.motor(e).cx,
                                                 "SELECT * FROM ventas")
    assert filas, "sin plan contra la base del cliente"
    filas_demo, _ = esquema_visual.plan_de_ejecucion(fuente.motor(e).cx,
                                                     "SELECT * FROM cobranzas")
    assert filas_demo == [], "el plan encontró una tabla de la demo"


@test("equipo: las tablas para asignar a un usuario son las del cliente")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    perm = {"tablas": ["ventas"]}
    vis = equipo.tablas_visibles(fuente.motor(e).catalogo, perm)
    assert set(vis["tablas"]) == {"ventas"}


@test("ejemplos: con la fuente del cliente hablan de SUS tablas, no de cobranzas")
def _():
    demo_ej = ["¿Cuánto cobramos por mes en 2026?", "Top 10 clientes con más deuda"]
    plantillas = ["¿Cuántos registros tiene {tabla}?", "Primeras 10 filas de {tabla}"]
    e = estado_con_demo()
    assert fuente.ejemplos(e, demo_ej, plantillas) == demo_ej
    pasar_a_usuario(e)
    ej = fuente.ejemplos(e, demo_ej, plantillas)
    assert len(ej) == 4 and len(set(ej)) == 4, ej
    assert all(("ventas" in x or "productos" in x) for x in ej), ej
    assert not any(x in demo_ej for x in ej)


@test("un archivo subido (CSV→SQLite) también reemplaza a la demo")
def _():
    ruta_arch = os.path.join(TMP, "mvsql_archivo_abc.db")
    _crear(ruta_arch, "CREATE TABLE datos (a INTEGER, b TEXT); INSERT INTO datos VALUES (1,'x');")
    e = estado_con_demo()
    fuente.usar_usuario(e, fabricar(ruta_arch), "ventas.csv", "archivo:ventas.csv:10")
    assert fuente.activa(e)["tipo"] == fuente.USUARIO
    assert fuente.activa(e)["etiqueta"] == "ventas.csv"
    assert set(fuente.motor(e).catalogo["tablas"]) == {"datos"}


@test("conectar cartera_demo.db a mano sigue marcado como demo (el indicador no miente)")
def _():
    e = {}
    fuente.usar_usuario(e, fabricar(DEMO_DB), "cartera_demo.db")
    assert fuente.es_demo(e)


print("\n== Volver a la demo ==")


@test("«Volver a la demo» trae la demo y borra lo derivado del cliente")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    cx_user = fuente.motor(e).cx
    e["resultado"] = {"sql": "SELECT * FROM ventas"}
    e["eda_fuente"] = "ventas"
    assert fuente.usar_demo(e, fabricar)
    assert fuente.es_demo(e)
    assert set(fuente.motor(e).catalogo["tablas"]) == TABLAS_DEMO
    assert e["resultado"] is None and "eda_fuente" not in e
    assert cx_user._con is None, "la conexión del cliente quedó abierta"


@test("si la demo no está, volver deja SIN fuente, nunca la del cliente colgada")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    original = fuente.RUTA_DEMO
    fuente.RUTA_DEMO = os.path.join(TMP, "no_existe.db")
    try:
        assert fuente.usar_demo(e, fabricar) is False
        assert fuente.motor(e) is None and fuente.activa(e) is None
    finally:
        fuente.RUTA_DEMO = original


@test("asegurar() no pisa la fuente del cliente en los reruns siguientes")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    for _ in range(3):
        fuente.asegurar(e, fabricar)
    assert fuente.activa(e)["tipo"] == fuente.USUARIO


@test("cerrar sesión (olvidar) → el próximo rerun vuelve a la demo")
def _():
    e = estado_con_demo()
    pasar_a_usuario(e)
    fuente.olvidar(e)
    assert fuente.motor(e) is None
    fuente.asegurar(e, fabricar)
    assert fuente.es_demo(e)


print("\n== app.py usa el resolvedor y nada más ==")

APP = os.path.join(RAIZ, "app.py")
FUENTE_APP = open(APP, encoding="utf-8").read()


@test("app.py no lee ni escribe la conexión por fuera de fuente.py")
def _():
    directos = re.findall(r"(?:ss|st\.session_state)\s*(?:\.motor\b|\[\s*['\"]motor['\"]\s*\])",
                          FUENTE_APP)
    assert not directos, f"accesos directos a la conexión: {directos}"
    assert FUENTE_APP.count("fuente.motor(ss)") >= 15, "¿se dejó de usar el resolvedor?"


@test("el selector SQLite ya no viene precargado con la demo")
def _():
    assert 'value="cartera_demo.db"' not in FUENTE_APP


@test("los textos nuevos están en los tres idiomas")
def _():
    import ast
    arbol = ast.parse(FUENTE_APP)
    T = None
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", "") == "T":
            T = ast.literal_eval(nodo.value)
    assert T, "no se encontró el diccionario T"
    for clave in ("fuente_activa", "fuente_demo", "fuente_usuario", "fuente_volver",
                  "fuente_ninguna", "ej_contar", "ej_primeras"):
        for lang in ("es", "en", "pt"):
            assert T[lang].get(clave), f"falta {clave} en {lang}"
    for lang in ("es", "en", "pt"):
        assert "{nombre}" in T[lang]["fuente_usuario"]
        assert "{tabla}" in T[lang]["ej_contar"] and "{tabla}" in T[lang]["ej_primeras"]


print("\n== La app real (Streamlit AppTest) ==")


@test("conectar la base propia cambia TODA la pantalla; volver trae la demo")
def _():
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("      (streamlit no instalado: se saltea el arranque real)")
        return

    marcas = [os.path.join(RAIZ, ".eula_aceptado"), os.path.join(RAIZ, ".mvsql_trial.json")]
    previos = {m: (open(m, "rb").read() if os.path.exists(m) else None) for m in marcas}
    # Prueba recién instalada: una marca de trial vieja de esta PC dejaría
    # la app en la pantalla de «tu prueba terminó». Se restauran al final.
    for m in marcas:
        if os.path.exists(m):
            os.remove(m)
    try:
        at = AppTest.from_file(APP, default_timeout=240)
        at.run()
        if at.checkbox and not at.selectbox:     # pantalla del EULA
            at.checkbox[0].check().run()
            at.button[0].click().run()
        assert not at.exception, [e.value for e in at.exception]

        def textos():
            partes = [c.value for c in at.caption] + [m.value for m in at.markdown]
            partes += [x.value for x in at.info] + [x.value for x in at.success]
            partes += [b.label for b in at.button]
            return "\n".join(str(p) for p in partes)

        antes = textos()
        assert "(demo)" in antes, "al arrancar no indica que está en la demo"
        assert "**clientes**" in antes or "**cobranzas**" in antes, \
            "el esquema de la demo no aparece al arrancar"

        motor_sel = [s for s in at.selectbox if s.options and "PostgreSQL" in s.options]
        assert motor_sel, "no se encontró el selector de motor"
        motor_sel[0].set_value("sqlite").run()
        ruta_in = [x for x in at.text_input if x.label == "Archivo .db"]
        assert ruta_in, "no aparece el campo de ruta SQLite"
        assert ruta_in[0].value == "", "el campo SQLite viene precargado"
        ruta_in[0].input(USER_DB).run()
        [b for b in at.button if b.label == "Conectar"][0].click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert not at.error, [e.value for e in at.error]

        despues = textos()
        assert "mis_ventas.db" in despues, "el indicador no muestra la fuente del cliente"
        assert "(demo)" not in despues, "sigue diciendo demo con la base del cliente"
        for t in TABLAS_DEMO:
            assert f"**{t}**" not in despues, f"el esquema sigue mostrando '{t}' de la demo"
        assert "**ventas**" in despues and "**productos**" in despues
        assert "Cuánto cobramos" not in despues, "siguen los ejemplos de cobranzas de la demo"

        [b for b in at.button if b.label == "Volver a la demo"][0].click().run()
        assert not at.exception, [e.value for e in at.exception]
        final = textos()
        assert "(demo)" in final and "**ventas**" not in final
    finally:
        for m, contenido in previos.items():
            if contenido is None:
                if os.path.exists(m):
                    os.remove(m)
            else:
                open(m, "wb").write(contenido)


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
