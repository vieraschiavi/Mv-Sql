# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_control.py — pestaña «Control»: el resultado es confiable o avisa
==================================================================
La validación del motor dice que la consulta es de solo lectura y que
las tablas existen. No dice si el número está bien. Estos tests plantan
en un SQLite los dos errores de join que pasan en verde —clave repetida
(duplica filas) y claves sin pareja (INNER JOIN que descarta)— más
columnas con defectos, y verifican que el Control los encuentre, y que
NO acuse nada en un resultado sano.

Runner propio (sin pytest), igual que el resto de app-python/tests.
"""
import os
import sqlite3
import sys
import tempfile
from decimal import Decimal

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

try:
    import pandas as pd  # noqa: E402
except ImportError:
    # El CI corre `npm ci` y nada más: sin pandas. Lo que no lo necesita
    # (leer joins, verificarlos contra la base, textos, instalador) corre
    # igual; el perfil de columnas y la app se saltean, como en el resto
    # de app-python/tests.
    pd = None

import control_resultado as C  # noqa: E402
from conectores import ConexionBD  # noqa: E402

pasadas = falladas = 0


def test(nombre):
    def deco(fn):
        global pasadas, falladas
        try:
            fn()
            print(f"  ✓ {nombre}")
            pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}")
            falladas += 1
    return deco


def _con_pandas(fn):
    def envuelto():
        if pd is None:
            print("      (pandas no instalado: se saltea)")
            return
        fn()
    return envuelto


_DIR = tempfile.mkdtemp(prefix="mvsql_control_")
_DB = os.path.join(_DIR, "control.db")


def _armar_base():
    con = sqlite3.connect(_DB)
    con.executescript("""
        CREATE TABLE clientes (cliente_id INTEGER PRIMARY KEY, nombre TEXT, pais TEXT);
        CREATE TABLE productos (producto_id INTEGER PRIMARY KEY, nombre TEXT);
        -- precios con la clave REPETIDA: dos precios vigentes para el producto 1
        CREATE TABLE precios (producto_id INTEGER, precio REAL);
        CREATE TABLE ventas (venta_id INTEGER PRIMARY KEY, cliente_id INTEGER,
                             producto_id INTEGER, fecha TEXT, importe REAL);
        INSERT INTO clientes VALUES (1,'Ana','AR'),(2,'Beto','UY'),(3,'Caro','AR');
        INSERT INTO productos VALUES (1,'A'),(2,'B');
        INSERT INTO precios VALUES (1,10.0),(1,12.0),(2,20.0);
        -- la venta 4 es de un cliente (99) que no existe
        INSERT INTO ventas VALUES
            (1,1,1,'2026-09-01',100),(2,2,2,'2026-09-02',200),
            (3,3,1,'2026-09-03',300),(4,99,2,'2026-09-04',400),
            (5,1,2,'2026-09-05',500);
    """)
    con.commit()
    con.close()


_armar_base()
CX = ConexionBD("sqlite", ruta=_DB).conectar()
CAT = CX.extraer_catalogo()


# ──────────────────────────────────────────────────────────────
print("\n== Lectura de los JOIN del SQL ==")


@test("alias, esquema y tipo de join")
def _():
    sql = """SELECT v.importe FROM dbo.ventas AS v
             LEFT JOIN [dbo].[clientes] c ON c.cliente_id = v.cliente_id
             INNER JOIN productos p ON v.producto_id = p.producto_id
             WHERE v.fecha >= '2026-09-01'"""
    j = C.joins_del_sql(sql)
    assert len(j) == 2, j
    assert j[0]["tipo"] == "LEFT" and j[0]["base"] == "dbo.ventas"
    assert j[0]["unida"] == "[dbo].[clientes]"
    assert j[0]["col_base"] == ["cliente_id"] and j[0]["col_unida"] == ["cliente_id"]
    assert j[1]["tipo"] == "INNER" and j[1]["col_base"] == ["producto_id"]


@test("clave compuesta, JOIN sin alias y comentarios/literales que no confunden")
def _():
    sql = """-- JOIN falso ON a.x = b.y en un comentario
             SELECT * FROM ventas JOIN precios
               ON precios.producto_id = ventas.producto_id AND precios.precio = ventas.importe
             WHERE ventas.fecha <> 'JOIN x ON y.a = z.b'"""
    j = C.joins_del_sql(sql)
    assert len(j) == 1, j
    assert j[0]["col_base"] == ["producto_id", "importe"]
    assert j[0]["col_unida"] == ["producto_id", "precio"]


@test("un join contra un CTE se marca como no verificable, no se inventa")
def _():
    sql = """WITH tot AS (SELECT cliente_id, SUM(importe) t FROM ventas GROUP BY cliente_id)
             SELECT c.nombre, tot.t FROM clientes c JOIN tot ON tot.cliente_id = c.cliente_id"""
    j = C.joins_del_sql(sql)
    assert len(j) == 1 and j[0]["verificable"] is False


@test("sin JOIN (o CROSS JOIN) no hay nada que verificar")
def _():
    assert C.joins_del_sql("SELECT importe FROM ventas WHERE importe > 0") == []
    assert C.joins_del_sql("SELECT 1 FROM ventas CROSS JOIN productos") == []
    assert C.joins_del_sql("") == []


@test("PostgreSQL: las columnas citadas se usan TAL CUAL (no se pasan a minúsculas)")
def _():
    sql = 'SELECT 1 FROM "Ventas" v JOIN "Clientes" c ON c."Id" = v."ClienteId"'
    j = C.joins_del_sql(sql)[0]
    assert j["col_base"] == ['"ClienteId"'] and j["col_unida"] == ['"Id"'], j
    q = C.sql_claves_repetidas(j["base"], j["col_base"], "PostgreSQL")
    assert 'SELECT "ClienteId" FROM "Ventas"' in q, q


@test("ON con vigencia, constante, OR o función: no se verifica (evita el N:N falso)")
def _():
    base = "SELECT 1 FROM ventas v JOIN precios p ON "
    for cond in ("p.producto_id = v.producto_id AND v.fecha BETWEEN p.desde AND p.hasta",
                 "p.producto_id = v.producto_id AND p.vigente = 1",
                 "p.id = v.pid OR p.id = v.pid2",
                 "UPPER(p.cod) = UPPER(v.cod)",
                 "p.cod = LEFT(v.cod, 3)"):
        j = C.joins_del_sql(base + cond)
        assert len(j) == 1 and not j[0]["verificable"], (cond, j)
        assert j[0]["motivo"] == "on_complejo", (cond, j)


@test("ON que cruza contra DOS tablas distintas no se verifica a medias")
def _():
    j = C.joins_del_sql("SELECT 1 FROM a JOIN b ON b.k = a.k JOIN c ON c.x = a.x AND c.y = b.y")
    assert j[0]["verificable"] and j[1]["motivo"] == "on_complejo", j


@test("alias reusado en una subconsulta y tabla derivada no confunden la base")
def _():
    j = C.joins_del_sql("SELECT 1 FROM ventas v JOIN clientes c ON c.id = v.cid "
                        "WHERE v.x IN (SELECT v.x FROM devoluciones v)")
    assert j[0]["base"] == "ventas", j
    j = C.joins_del_sql("SELECT 1 FROM (SELECT id FROM t) sueldos "
                        "JOIN clientes c ON c.id = sueldos.id")
    assert not j[0]["verificable"] and j[0]["motivo"] == "cte", j


@test("USING, NATURAL, JOIN a subconsulta y FROM a, b se listan como no leídos")
def _():
    for sql in ("SELECT 1 FROM ventas JOIN clientes USING (id)",
                "SELECT 1 FROM ventas NATURAL JOIN clientes",
                "SELECT 1 FROM ventas v JOIN (SELECT id FROM clientes) x ON x.id = v.cid",
                "SELECT 1 FROM ventas v, clientes c WHERE c.id = v.cid"):
        j = C.joins_del_sql(sql)
        assert j and j[0]["motivo"] == "no_leido" and not j[0]["verificable"], (sql, j)


@test("self-join y hints de SQL Server (LEFT HASH JOIN)")
def _():
    j = C.joins_del_sql("SELECT 1 FROM emp JOIN emp m ON m.id = emp.jefe")
    assert j[0]["verificable"] and j[0]["col_base"] == ["jefe"] and j[0]["col_unida"] == ["id"], j
    j = C.joins_del_sql("SELECT 1 FROM ventas v LEFT HASH JOIN clientes c ON c.id = v.cid")
    assert j[0]["tipo"] == "LEFT", j


# ──────────────────────────────────────────────────────────────
print("\n== Verificación de los joins contra la base ==")


@test("N:1 sano: ventas → productos (PK) sin huérfanas → ok")
def _():
    r = C.verificar_joins(CX, "SELECT * FROM ventas v JOIN productos p "
                              "ON p.producto_id = v.producto_id", CAT)
    assert r[0]["relacion"] == "N:1" and r[0]["estado"] == "ok", r
    assert r[0]["huerfanas"] == 0


@test("INNER JOIN que descarta filas: 1 venta sin cliente → revisar")
def _():
    r = C.verificar_joins(CX, "SELECT * FROM ventas v JOIN clientes c "
                              "ON c.cliente_id = v.cliente_id", CAT)
    assert r[0]["huerfanas"] == 1 and r[0]["motivo"] == "huerfanas_inner", r
    # Y es verdad: el INNER JOIN trae 4 de las 5 ventas.
    _c, filas, _ = CX.ejecutar("SELECT COUNT(*) FROM ventas v JOIN clientes c "
                               "ON c.cliente_id = v.cliente_id", limite=None)
    assert filas[0][0] == 4


@test("LEFT JOIN con huérfanas: no se pierden filas, salen con nulos → revisar")
def _():
    r = C.verificar_joins(CX, "SELECT * FROM ventas v LEFT JOIN clientes c "
                              "ON c.cliente_id = v.cliente_id", CAT)
    assert r[0]["motivo"] == "huerfanas_left", r


@test("clave repetida del lado unido: N:N → error, y el total sale inflado de verdad")
def _():
    sql = "SELECT * FROM ventas v JOIN precios pr ON pr.producto_id = v.producto_id"
    r = C.verificar_joins(CX, sql, CAT)
    assert r[0]["repetidas_unida"] == 1 and r[0]["relacion"] == "N:N", r
    assert r[0]["estado"] == "error"
    _c, filas, _ = CX.ejecutar("SELECT COUNT(*) FROM ventas v JOIN precios pr "
                               "ON pr.producto_id = v.producto_id", limite=None)
    assert filas[0][0] == 7, "el join duplica: 5 ventas → 7 filas"


@test("1:N: clientes → ventas repite las columnas del cliente → revisar")
def _():
    r = C.verificar_joins(CX, "SELECT * FROM clientes c JOIN ventas v "
                              "ON v.cliente_id = c.cliente_id", CAT)
    assert r[0]["relacion"] == "1:N" and r[0]["estado"] == "revisar", r


@test("tabla fuera del catálogo o columna inexistente: no se consulta la base")
def _():
    llamadas = []
    r = C.verificar_joins(CX, "SELECT * FROM ventas v JOIN sueldos s ON s.id = v.venta_id",
                          CAT, ejecutar=lambda q: llamadas.append(q))
    assert r[0]["estado"] == "no_verificable" and r[0]["motivo"] == "fuera_catalogo"
    r = C.verificar_joins(CX, "SELECT * FROM ventas v JOIN clientes c ON c.inventada = v.venta_id",
                          CAT, ejecutar=lambda q: llamadas.append(q))
    assert r[0]["motivo"] == "fuera_catalogo" and not llamadas


@test("si la base tira error, se muestra el motivo (no se traga)")
def _():
    def falla(_q):
        raise RuntimeError("timeout del servidor")
    r = C.verificar_joins(CX, "SELECT * FROM ventas v JOIN precios pr "
                              "ON pr.producto_id = v.producto_id", CAT, ejecutar=falla)
    assert r[0]["motivo"] == "error_motor" and "timeout" in r[0]["error"]


@test("las consultas de control pasan la barrera de solo lectura")
def _():
    from conectores import asegurar_solo_lectura
    for dial in ("SQLite", "SQL Server", "MySQL / MariaDB", "PostgreSQL"):
        asegurar_solo_lectura(C.sql_claves_repetidas("dbo.Ventas", ["Cliente ID", "x"], dial))
        asegurar_solo_lectura(C.sql_huerfanas("dbo.Ventas", ["a"], "dbo.Clientes", ["b"], dial))
    assert "[Cliente ID]" in C.sql_claves_repetidas("t", ["Cliente ID"], "SQL Server")
    assert "`Cliente ID`" in C.sql_claves_repetidas("t", ["Cliente ID"], "MySQL / MariaDB")


# ──────────────────────────────────────────────────────────────
print("\n== Perfil de columnas del resultado ==")


def _alertas(perfil, col):
    return next(f for f in perfil if f["columna"] == col)["alertas"]


@test("resultado sano: sin alertas que cambien el semáforo → ok")
@_con_pandas
def _():
    df = pd.DataFrame({"cliente": ["Ana", "Beto", "Caro"], "importe": [100.0, 200.0, 300.0],
                       "fecha": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-09-03"])})
    p = C.perfil_columnas(df)
    assert C.semaforo(p, C.filas_duplicadas(df)) == "ok", p
    imp = next(f for f in p if f["columna"] == "importe")
    assert imp["tipo"] == "numero" and imp["suma"] == 600.0 and imp["minimo"] == 100.0
    fec = next(f for f in p if f["columna"] == "fecha")
    assert fec["tipo"] == "fecha" and fec["minimo"] == "2026-09-01"


@test("fechas de SQL Server como objetos datetime/date y 9999-12-31 fuera del rango de pandas")
@_con_pandas
def _():
    from datetime import date, datetime
    df = pd.DataFrame({"alta": [datetime(2026, 1, 5), datetime(9999, 12, 31), None],
                       "baja": [date(1900, 1, 1), date(2026, 3, 1), date(2026, 2, 1)],
                       "fecha_txt": ["01/09/2026", "15/09/2026", "30/08/2026"]})
    p = C.perfil_columnas(df)
    alta = next(f for f in p if f["columna"] == "alta")
    assert alta["tipo"] == "fecha" and "fecha_centinela" in alta["alertas"]
    assert alta["maximo"] == "9999-12-31"
    assert "fecha_centinela" in next(f for f in p if f["columna"] == "baja")["alertas"]
    txt = next(f for f in p if f["columna"] == "fecha_txt")
    assert txt["minimo"] == "30/08/2026" and txt["maximo"] == "15/09/2026", txt


@test("defectos plantados: vacía, nulos altos, fecha centinela, texto numérico, espacios")
@_con_pandas
def _():
    df = pd.DataFrame({
        "vacia": [None, None, None, None],
        "descuento": [1.0, None, None, 3.0],
        "fecha_alta": ["2026-01-01", "1900-01-01", "2026-02-01", "9999-12-31"],
        "codigo": ["10", "20", "30", "40"],
        "nombre": ["Ana ", "Beto", "Caro", "Dani"],
        "saldo": [10, -5, 3, 4],
        "moneda": ["USD", "USD", "USD", "USD"],
    })
    p = C.perfil_columnas(df)
    assert _alertas(p, "vacia")[0] == "vacia"
    assert "nulos_altos" in _alertas(p, "descuento")
    assert "fecha_centinela" in _alertas(p, "fecha_alta")
    assert "texto_numerico" in _alertas(p, "codigo")
    assert "espacios" in _alertas(p, "nombre")
    assert "negativos" in _alertas(p, "saldo")
    assert "constante" in _alertas(p, "moneda")
    assert C.semaforo(p) == "revisar"


@test("Decimal de SQL Server/PostgreSQL cuenta como número (tiene suma)")
@_con_pandas
def _():
    df = pd.DataFrame({"importe": [Decimal("10.50"), Decimal("4.50"), None]})
    f = C.perfil_columnas(df)[0]
    assert f["tipo"] == "numero" and abs(f["suma"] - 15.0) < 1e-9
    assert f["nulos"] == 1 and f["pct_nulos"] == 33.3


@test("date y datetime mezclados, bit con NULL, columnas repetidas y fechas M/D/Y")
@_con_pandas
def _():
    from datetime import date, datetime
    df = pd.DataFrame({"alta": [date(2026, 1, 1), datetime(2026, 3, 1, 10, 0), None]},
                      dtype=object)
    f = C.perfil_columnas(df)[0]
    assert f["tipo"] == "fecha" and f["maximo"] == "2026-03-01 10:00:00", f
    b = C.perfil_columnas(pd.DataFrame({"activo": [True, None, False]}, dtype=object))[0]
    assert b["tipo"] == "booleano" and b["suma"] is None, b
    d = C.perfil_columnas(pd.DataFrame([[1, "a"], [2, "b"]], columns=["x", "x"]))
    assert d[0]["tipo"] == "numero" and d[1]["tipo"] == "texto", d
    m = C.perfil_columnas(pd.DataFrame({"fecha": ["12/31/2024", "01/15/2025"]}))[0]
    assert m["minimo"] == "12/31/2024" and m["maximo"] == "01/15/2025", m
    x = C.perfil_columnas(pd.DataFrame({"fecha": ["2024-13-45", "2024-14-01"]}))[0]
    assert x["tipo"] == "texto", "un mes 13 no es una fecha"


@test("PostgreSQL: una consulta que falla hace rollback (la sesión sigue usable)")
def _():
    class Cur:
        def execute(self, *_a):
            raise RuntimeError("column does not exist")

    class Con:
        rollbacks = 0

        def cursor(self):
            return Cur()

        def rollback(self):
            Con.rollbacks += 1

    cx = ConexionBD("postgres")
    cx._con = Con()
    try:
        cx.ejecutar("SELECT x FROM t", limite=None)
        raise AssertionError("tenía que propagar el error")
    except RuntimeError:
        pass
    assert Con.rollbacks == 1


@test("filas duplicadas exactas se cuentan y cambian el semáforo")
@_con_pandas
def _():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    assert C.filas_duplicadas(df) == 1
    assert C.semaforo(C.perfil_columnas(df), 1) == "revisar"


@test("resultado vacío o con columnas repetidas no revienta")
@_con_pandas
def _():
    assert C.perfil_columnas(pd.DataFrame(columns=["a", "b"]))[0]["pct_nulos"] is None
    assert C.filas_duplicadas(pd.DataFrame()) == 0
    df = pd.DataFrame([[1, 2]], columns=["id", "id"])
    assert len(C.perfil_columnas(df)) == 2


@test("el semáforo toma el peor: un join N:N manda a error")
def _():
    assert C.semaforo([], 0, [{"estado": "error"}, {"estado": "ok"}]) == "error"
    assert C.semaforo([], 0, [{"estado": "no_verificable"}]) == "ok"


@test("a_dataframe traduce columnas y alertas")
@_con_pandas
def _():
    p = C.perfil_columnas(pd.DataFrame({"x": [None, None]}))
    d = C.a_dataframe(p, {"columna": "Column", "alertas": "Alerts"}, {"vacia": "Empty"})
    assert list(d.columns)[0] == "Column" and d["Alerts"].iloc[0] == "Empty"


# ──────────────────────────────────────────────────────────────
print("\n== La pestaña en la app (textos y cableado) ==")


@test("textos de la pestaña en ES/EN/PT, con cada alerta y cada motivo")
def _():
    import ast
    arbol = ast.parse(open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read())
    T = next(ast.literal_eval(n.value) for n in arbol.body
             if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "T")
    claves = ["ctl_titulo", "ctl_ok", "ctl_revisar", "ctl_error", "ctl_joins",
              "ctl_verificar", "ctl_sin_joins", "ctl_duplicadas", "ctl_descargar"]
    claves += [f"ctl_al_{a}" for a in C.SEVERIDAD]
    claves += [f"ctl_mot_{m}" for m in ("ok", "1n", "nn", "huerfanas_inner",
                                         "huerfanas_left", "cte", "fuera_catalogo",
                                         "error_motor", "on_complejo", "no_leido")]
    claves += ["ctl_no_verificables", "ctl_fallo"]
    for lang in ("es", "en", "pt"):
        faltan = [k for k in claves if k not in T[lang]]
        assert not faltan, f"{lang}: faltan {faltan}"


@test("la pestaña Control está cableada en app.py")
def _():
    src = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    assert "import control_resultado" in src
    assert "t['ctl_titulo']" in src or 't["ctl_titulo"]' in src


@test("botones de descarga y desplegables con texto legible (no gris sobre blanco)")
def _():
    src = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    for selector in ('[data-testid="stDownloadButton"] button', '[data-testid="stPopoverButton"]'):
        assert selector in src, f"falta el estilo de {selector}: hereda #e2e8f0 sobre fondo blanco"


@test("el instalador y el zip llevan control_resultado.py")
def _():
    nsi = open(os.path.join(RAIZ, "..", "installer", "mvsql.nsi"), encoding="utf-8").read()
    assert "control_resultado.py" in nsi, "installer/mvsql.nsi no lo copia: ImportError al abrir"


# ──────────────────────────────────────────────────────────────
print("\n== La app real (Streamlit AppTest) ==")

SQL_NN = ("SELECT v.venta_id, v.importe, pr.precio FROM ventas v "
          "JOIN precios pr ON pr.producto_id = v.producto_id")


def _app_conectada():
    """La app con el EULA aceptado y la base de prueba conectada."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(RAIZ, "app.py"), default_timeout=240)
    at.run()
    if at.checkbox and not at.selectbox:            # pantalla del EULA
        at.checkbox[0].check().run()
        at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    motor_sel = [x for x in at.selectbox if x.options and "PostgreSQL" in x.options]
    motor_sel[0].set_value("sqlite").run()
    [x for x in at.text_input if x.label == "Archivo .db"][0].input(_DB).run()
    [b for b in at.button if b.label == "Conectar"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _con_resultado(at, sql):
    cols, filas, _ = CX.ejecutar(sql, limite=None)
    at.session_state["resultado"] = {
        "pregunta": "control", "tablas_recuperadas": ["ventas", "precios"], "sql": sql,
        "valido": True, "problemas": [], "advertencias": [], "confianza": None,
        "supuestos": "", "columnas": cols, "filas": filas, "sql_ejecutado": sql,
        "error": None, "explicacion": None, "usa_cte": False, "recorte": None}
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def _con_streamlit(fn):
    def envuelto():
        try:
            import streamlit.testing.v1  # noqa: F401
        except ImportError:
            print("      (streamlit no instalado: se saltea el arranque real)")
            return
        anterior = os.environ.get("MVSQL_DATOS")
        os.environ["MVSQL_DATOS"] = _DIR           # EULA, trial y guardadas en el temporal
        try:
            fn()
        finally:
            if anterior is None:
                os.environ.pop("MVSQL_DATOS", None)
            else:
                os.environ["MVSQL_DATOS"] = anterior
    return envuelto


@test("la pestaña Control aparece, dibuja el perfil y detecta el join que duplica")
@_con_streamlit
def _():
    at = _app_conectada()
    _con_resultado(at, SQL_NN)
    assert "Control" in [x.label for x in at.tabs], [x.label for x in at.tabs]
    boton = [b for b in at.button if b.label == "Verificar joins contra la base"]
    assert boton, "no aparece el botón para verificar los joins"
    boton[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    errores = " ".join(str(e.value) for e in at.error)
    assert "duplicando filas" in errores, f"no avisa el join N:N: {errores!r}"
    textos = " ".join(str(d.value.to_csv()) for d in at.dataframe)
    assert "N:N" in textos, "la tabla de joins no muestra la relación N:N"


@test("Explorar sobre una tabla completa y Guardar consulta ya no revientan")
@_con_streamlit
def _():
    """Regresión: `fuente = st.selectbox(...)` pisaba el módulo `fuente`."""
    at = _app_conectada()
    _con_resultado(at, "SELECT venta_id, importe FROM ventas")
    at.selectbox(key="eda_fuente").set_value("ventas").run()
    assert not at.exception, [e.value for e in at.exception]
    rotos = [str(e.value) for e in at.error if "has no attribute" in str(e.value)]
    assert not rotos, rotos
    at.text_input(key="nombre_guardar").input("ventas del mes").run()
    at.button(key="btn_guardar").click().run()
    assert not at.exception, [e.value for e in at.exception]


CX.cerrar() if hasattr(CX, "cerrar") else None
print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
