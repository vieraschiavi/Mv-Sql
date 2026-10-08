# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_mercados_conformados.py — el contexto del negocio que manda la suite (mercados conformados, glosario, JOINs)
==================================================================================================================
Pedido: «sqlnlp al tener acceso a los mercados conformados dentro de Azure Analysis, para mejorar la precisión de
las respuestas». Con sólo nombres de tablas y columnas, «¿cuál es el share de Olmesartán?» se dividía por el total
del país: la canasta del mercado no está en ninguna columna. La suite ahora manda, junto con las tablas del MDW, los
mercados conformados de HQ, el glosario y las relaciones del modelo.

Se prueba:
  1. `tablas_externas.contexto` traduce relaciones y tablas clave a los nombres de la base SQLite.
  2. `MotorMVSQL.sumar_contexto` suma los JOIN del modelo al catálogo y a las fichas, y descarta lo que no existe
     o lo que el rol no ve.
  3. El prompt lleva «DEFINICIONES DEL NEGOCIO» (también en privacidad estricta: son definiciones, no datos).
  4. Una pregunta de mercado o share suma siempre las tablas de mercados conformados; una que no, no.
  5. Si el modelo ya trae la columna de mercado conformado, el prompt la nombra.
  6. Las columnas de mercado guardan hasta 100 valores de ejemplo; el resto, 8.
  7. La conexión directa a Analysis Services arma el mismo paquete, best-effort.
"""
import os
import sqlite3
import sys
import tempfile
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

# motor.py importa sklearn (RAG real) y requests (proveedores): acá no se usan, se stubean como en test_privacidad.
for _n in ("sklearn", "sklearn.feature_extraction", "sklearn.feature_extraction.text", "sklearn.metrics",
           "sklearn.metrics.pairwise"):
    sys.modules.setdefault(_n, types.ModuleType(_n))
if not hasattr(sys.modules["sklearn.feature_extraction.text"], "TfidfVectorizer"):
    sys.modules["sklearn.feature_extraction.text"].TfidfVectorizer = object
    sys.modules["sklearn.metrics.pairwise"].cosine_similarity = lambda *a, **k: None
sys.modules.setdefault("requests", types.ModuleType("requests"))

import catalogo  # noqa: E402
import conector_aas  # noqa: E402
import motor  # noqa: E402
import tablas_externas as TE  # noqa: E402

pasadas = falladas = 0


def test(nombre):
    def deco(fn):
        global pasadas, falladas
        try:
            fn(); print(f"  ✓ {nombre}"); pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}"); falladas += 1
    return deco


class Tabla:
    """Lo único que `tablas_externas.nombres` le mira a un DataFrame: sus columnas (sin pandas)."""
    def __init__(self, *columnas):
        self.columns = list(columnas)


class Recuperador:
    """Doble del RAG: devuelve la primera ficha (la de ventas), como haría TF-IDF con «ventas»."""
    def __init__(self, fichas):
        self.fichas = fichas

    def recuperar(self, pregunta, k=4):
        return self.fichas[:1], [0.8]


motor.RecuperadorEsquema = Recuperador


def _col(nombre, tipo="TEXT"):
    return {"columna": nombre, "tipo": tipo, "nullable": True, "pk": False}


def _catalogo():
    return {"tablas": {
        "ventas": {"n_filas": 3, "muestras": {}, "columnas": [_col("CodProducto"), _col("ATC4"),
                                                              _col("Unidades", "INTEGER")]},
        "producto": {"n_filas": 2, "muestras": {}, "columnas": [_col("CodProducto"), _col("Molecula")]},
        "mercado_conformado_ct": {"n_filas": 2, "muestras": {}, "columnas": [_col("mercado"), _col("ct")]},
    }, "fks": [], "joins_inferidos": {}}


class ConexionFalsa:
    dialecto = "sqlite"

    def ejecutar(self, sql, limite=5000, params=None):
        return (["total_unidades"], [[10]], sql)


def _motor(cat=None):
    m = motor.MotorMVSQL.__new__(motor.MotorMVSQL)
    m.cx, m.ia = ConexionFalsa(), {"proveedor": "falso"}
    m.catalogo = cat or _catalogo()
    m.fichas = catalogo.catalogo_a_fichas(m.catalogo)
    m.recuperador = Recuperador(m.fichas)
    m.conocimiento, m.tablas_clave = "", []
    llamadas = []

    def completar(system, user, max_tokens=1500):
        llamadas.append(system)
        return "SQL:\nSELECT SUM(Unidades) AS total_unidades FROM ventas\nCONFIANZA: 90\nSUPUESTOS: ninguno"

    m._completar = completar
    return m, llamadas


REL = {"tabla_origen": "ventas", "columna_origen": "CodProducto", "tabla_destino": "producto",
       "columna_destino": "CodProducto"}

print("\n== tablas_externas.contexto: nombres del modelo → nombres de la base ==")


@test("relaciones y tablas clave salen con los nombres que tiene la base SQLite")
def _():
    paquete = {"tablas": {"Venta Interna": Tabla("Cod Producto", "Unidades"), "Dim Producto": Tabla("Cod Producto"),
                          "mercado_conformado_ct": Tabla("mercado", "ct")},
               "conocimiento": "MERCADOS CONFORMADOS…",
               "relaciones": [
                   {"tabla_origen": "venta interna", "columna_origen": "cod producto",
                    "tabla_destino": "Dim Producto", "columna_destino": "Cod Producto"},
                   {"tabla_origen": "Venta Interna", "columna_origen": "Cod Producto",
                    "tabla_destino": "Calendario", "columna_destino": "Fecha"},      # tabla que no vino
                   {"tabla_origen": "Venta Interna"}],                               # incompleta
               "tablas_clave": ["mercado_conformado_ct", "mercado_conformado"]}
    conoc, rels, clave = TE.contexto(paquete)
    assert conoc == "MERCADOS CONFORMADOS…"
    assert rels == [{"tabla_origen": "venta_interna", "columna_origen": "Cod_Producto",
                     "tabla_destino": "dim_producto", "columna_destino": "Cod_Producto"}], rels
    assert clave == ["mercado_conformado_ct"], clave


@test("un paquete viejo (sin conocimiento ni relaciones) sigue andando")
def _():
    assert TE.contexto({"tablas": {"t": Tabla("a")}}) == ("", [], [])


print("\n== MotorMVSQL.sumar_contexto ==")


@test("los JOIN del modelo entran al catálogo y a las fichas; lo inexistente se descarta")
def _():
    m, _ = _motor()
    n = m.sumar_contexto("defs", [REL, REL, {**REL, "columna_destino": "NoExiste"},
                                  {**REL, "tabla_destino": "oculta"}], ["mercado_conformado_ct", "no_esta"])
    assert n == 1 and m.catalogo["fks"] == [REL], m.catalogo["fks"]
    ficha = next(f for f in m.fichas if f["tabla"] == "ventas")
    assert "Relaciones (JOINs):" in ficha["texto"] and "ventas.CodProducto -> producto.CodProducto" in ficha["texto"]
    assert "ventas.CodProducto -> producto.CodProducto" in ficha["texto_min"]
    assert m.tablas_clave == ["mercado_conformado_ct"]


@test("el texto de definiciones se recorta al tope")
def _():
    m, _ = _motor()
    m.sumar_contexto("\n".join(f"línea {i} " + "x" * 100 for i in range(400)))
    assert len(m.conocimiento) <= motor.TOPE_CONOCIMIENTO + 40 and m.conocimiento.endswith("recortadas]")


print("\n== el prompt ==")


@test("el prompt lleva las definiciones del negocio, también en privacidad estricta")
def _():
    for privado in (False, True):
        m, llamadas = _motor()
        m.sumar_contexto("MERCADOS CONFORMADOS: share = marca / canasta {con llaves}")
        r = m.responder("total de unidades", explicar=False, privado=privado)
        assert r["valido"] and r["error"] is None, r
        assert "DEFINICIONES DEL NEGOCIO" in llamadas[0]
        assert "share = marca / canasta {con llaves}" in llamadas[0]
        assert llamadas[0].index("DEFINICIONES DEL NEGOCIO") < llamadas[0].index("ESQUEMA DISPONIBLE")


@test("sin contexto el prompt queda como antes")
def _():
    cat = _catalogo()
    del cat["tablas"]["mercado_conformado_ct"]
    m, llamadas = _motor(cat)
    m.responder("total de unidades", explicar=False)
    assert "DEFINICIONES DEL NEGOCIO" not in llamadas[0]


@test("una pregunta de share suma las tablas de mercados conformados; una de otra cosa, no")
def _():
    m, llamadas = _motor()
    m.sumar_contexto("defs", (), ["mercado_conformado_ct"])
    r = m.responder("¿cuál es el share de Olmesartán en su mercado?", explicar=False)
    assert r["tablas_recuperadas"] == ["ventas", "mercado_conformado_ct"], r["tablas_recuperadas"]
    assert "TABLA: mercado_conformado_ct" in llamadas[0]
    for pregunta in ("MS% de Pantoprazol", "market share by brand", "participação no mercado"):
        assert "mercado_conformado_ct" in m.responder(pregunta, explicar=False)["tablas_recuperadas"], pregunta
    assert m.responder("total de unidades", explicar=False)["tablas_recuperadas"] == ["ventas"]


@test("si el modelo ya trae el mercado conformado, el prompt lo nombra (y no confunde las tablas de la suite)")
def _():
    cat = _catalogo()
    cat["tablas"]["ventas"]["columnas"].append(_col("Mercado_Conformado"))
    cat["tablas"]["MercadoConformadoHQ"] = {"n_filas": 1, "muestras": {}, "columnas": [_col("Mercado")]}
    m, llamadas = _motor(cat)
    m.sumar_contexto("defs", (), ["mercado_conformado_ct"])
    m.responder("total de unidades", explicar=False)
    assert "ventas.Mercado_Conformado" in llamadas[0] and "MercadoConformadoHQ (tabla)" in llamadas[0]
    assert "mercado_conformado_ct.mercado" not in llamadas[0].split("ESQUEMA DISPONIBLE")[0]
    assert motor.columnas_de_mercado_conformado(_catalogo()) == ["mercado_conformado_ct (tabla)"]


print("\n== valores de ejemplo de las columnas de mercado ==")


@test("una columna de mercado guarda hasta 100 valores; una común, 8")
def _():
    ruta = os.path.join(tempfile.mkdtemp(), "m.db")
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE ventas (Mercado TEXT, ATC4 TEXT, Cliente TEXT, Unidades INTEGER)")
    con.executemany("INSERT INTO ventas VALUES (?, ?, ?, ?)",
                    [(f"MERCADO {i:03d}", f"C{i:02d}A0", f"Cliente {i}", i) for i in range(150)])
    con.commit()
    con.close()
    cat = catalogo.extraer_catalogo_sqlite(ruta)
    mues = cat["tablas"]["ventas"]["muestras"]
    assert len(mues["Mercado"]) == catalogo.MUESTRAS_MERCADO == 100
    assert len(mues["ATC4"]) == 100 and len(mues["Cliente"]) == catalogo.MUESTRAS == 8
    ficha = catalogo.catalogo_a_fichas(cat)[0]
    assert "MERCADO 099" in ficha["texto"] and "MERCADO 000" not in ficha["texto_min"]
    for col, mucho in (("Mercado", True), ("mercado_conformado", True), ("ct", True), ("ATC4", True),
                       ("Molécula", True), ("Área", True), ("Región", True), ("Cliente", False), ("Producto", False)):
        assert (catalogo.muestras_para(col) == 100) is mucho, col


print("\n== conexión directa a Analysis Services ==")


class Armador:
    def paquete(self, etiqueta, tablas, bims=()):
        return {"etiqueta": etiqueta, "tablas": {**tablas, "mercado_conformado_ct": Tabla("mercado", "ct")},
                "conocimiento": "defs", "relaciones": [], "tablas_clave": ["mercado_conformado_ct"],
                "bims": list(bims)}


@test("arma el paquete con las relaciones del modelo; si no puede leerlas, avisa y sigue")
def _():
    ok = types.SimpleNamespace(estructura=lambda srv, mod, tok: {"model": {"relationships": []}})
    p, avisos = conector_aas.contexto("asazure://x/y", "MDW", "AAS · MDW", {"Venta": Tabla("a")}, AS=ok,
                                      armador=Armador())
    assert avisos == [] and p["bims"] == [("MDW", {"model": {"relationships": []}})]
    assert set(p["tablas"]) == {"Venta", "mercado_conformado_ct"} and p["conocimiento"] == "defs"

    def falla(*a):
        raise RuntimeError("sin permiso de administrador")
    p, avisos = conector_aas.contexto("asazure://x/y", "MDW", "AAS · MDW", {"Venta": Tabla("a")},
                                      AS=types.SimpleNamespace(estructura=falla), armador=Armador())
    assert p["bims"] == [] and "Venta" in p["tablas"]
    assert len(avisos) == 1 and "sin permiso de administrador" in avisos[0] and "JOIN" in avisos[0]


@test("sin el armador de la suite, las tablas pasan igual y se avisa")
def _():
    orig = conector_aas.contexto_suite
    conector_aas.contexto_suite = lambda: None
    try:
        p, avisos = conector_aas.contexto("asazure://x/y", "MDW", "AAS · MDW", {"Venta": Tabla("a")})
    finally:
        conector_aas.contexto_suite = orig
    assert p == {"etiqueta": "AAS · MDW", "tablas": {"Venta": p["tablas"]["Venta"]}}
    assert len(avisos) == 1 and "mercados conformados" in avisos[0]


@test("la app suma el contexto en los dos caminos (lo que manda la suite y la conexión directa)")
def _():
    app = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    assert app.count(".sumar_contexto(*tablas_externas.contexto(") == 2
    assert "conector_aas.contexto(aas_srv, aas_mod" in app
    # después del recorte del rol: el motor sale de _armar_motor y recién ahí se le suma el contexto
    assert app.index("_m_ext = _armar_motor(") < app.index("_m_ext.sumar_contexto(")


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
