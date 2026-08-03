"""Qué viaja (y qué NO viaja) al proveedor de IA. Correr: python3 tests/test_privacidad.py

La landing dice "tus datos no salen de tu red". Este archivo convierte esa
frase de marketing en un invariante con test:

  - Para GENERAR el SQL viajan: la pregunta + los nombres de tablas y
    columnas de las tablas relevantes (el "esquema"). Ni una fila.
  - Para el ANÁLISIS escrito del resultado viaja una muestra de HASTA 20
    filas — eso es lo que la landing tiene que decir, ni más ni menos.
  - Con explicar=False (modo privacidad estricta de la app): exactamente
    UNA llamada a la IA y ningún valor de ninguna fila en ningún prompt.

Si alguien mete filas en el prompt de generación, o sube el tope de 20 sin
tocar la landing, esto falla con el valor exacto que se filtró.

Nota técnica: motor.py importa sklearn (para el RAG real) y requests (para
los proveedores reales). Este test no usa ninguno de los dos — reemplaza el
recuperador y _completar por dobles — así que se stubean los módulos antes
de importar, para mantener la promesa de requirements.txt: los tests corren
con la biblioteca estándar sola, sin pip install.
"""
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

# ── stubs para que `import motor` no exija sklearn/requests ──────────
for nombre in ("sklearn", "sklearn.feature_extraction",
               "sklearn.feature_extraction.text", "sklearn.metrics",
               "sklearn.metrics.pairwise"):
    sys.modules.setdefault(nombre, types.ModuleType(nombre))
sys.modules["sklearn.feature_extraction.text"].TfidfVectorizer = object
sys.modules["sklearn.metrics.pairwise"].cosine_similarity = lambda *a, **k: None
sys.modules.setdefault("requests", types.ModuleType("requests"))

import motor  # noqa: E402
import catalogo  # noqa: E402  (stdlib puro: sqlite3, json — no necesita stubs)

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


# Dos clases de dato del cliente, con centinelas distintos para saber CUÁL
# se filtró y por qué camino:
#   - MUESTRA: valores reales de una columna de texto que catalogo.py toma del
#     esquema y mete en la ficha. Es el que el agente encontró viajando en la
#     GENERACIÓN del SQL, y que el test viejo no veía porque usaba una ficha
#     escrita a mano en vez de catalogo_a_fichas.
#   - FILA: valores del resultado de la consulta, que van en el ANÁLISIS.
CANARIO_MUESTRA = "ACME_CONFIDENCIAL_771"
FILA_1 = ("Cliente Uno", 98765.43)
FILA_2 = ("Cliente Dos", 12345.67)
CENTINELAS_FILA = [str(v) for fila in (FILA_1, FILA_2) for v in fila]

SQL_CANONICO = "SELECT nombre, saldo FROM clientes"


class ConexionFalsa:
    dialecto = "sqlite"

    def ejecutar(self, sql, limite=5000, params=None):
        return (["nombre", "saldo"], [list(FILA_1), list(FILA_2)], sql)


def armar_motor():
    """Motor real, pero con las fichas armadas por catalogo_a_fichas DE VERDAD
    (con muestras), no un doble a mano. Es la única forma de que el test vea el
    camino donde vivía la fuga."""
    m = motor.MotorMVSQL.__new__(motor.MotorMVSQL)
    m.cx = ConexionFalsa()

    # Catálogo con una MUESTRA de columna de texto que lleva el centinela:
    # exactamente lo que catalogo.py produce para una base real.
    cat = {"tablas": {"clientes": {
        "n_filas": 2,
        "columnas": [
            {"columna": "id", "tipo": "INTEGER", "pk": True, "nullable": False},
            {"columna": "nombre", "tipo": "TEXT", "pk": False, "nullable": True},
            {"columna": "saldo", "tipo": "REAL", "pk": False, "nullable": True},
        ],
        "muestras": {"nombre": [CANARIO_MUESTRA, "Otro Cliente"]},
    }}, "fks": [], "joins_inferidos": {}}
    fichas = catalogo.catalogo_a_fichas(cat)          # <- la función real

    class RecuperadorReal:
        def recuperar(self, pregunta, k=4):
            return (fichas, [0.9])

    m.recuperador = RecuperadorReal()
    m.catalogo = cat
    llamadas = []

    def completar_falso(system, user, max_tokens=1500):
        llamadas.append({"system": system, "user": user})
        if len(llamadas) == 1:
            return f"SQL:\n{SQL_CANONICO}\nCONFIANZA: 93\nSUPUESTOS: ninguno"
        return "El saldo total es alto y se concentra en dos clientes."

    m._completar = completar_falso
    return m, llamadas


print("\n== catalogo_a_fichas: separa esquema de datos de ejemplo ==")


@test("la ficha normal lleva los valores de ejemplo; la 'min' no")
def _():
    cat = {"tablas": {"t": {
        "n_filas": 1, "muestras": {"c": [CANARIO_MUESTRA]},
        "columnas": [{"columna": "c", "tipo": "TEXT", "pk": False, "nullable": True}],
    }}, "fks": [], "joins_inferidos": {}}
    f = catalogo.catalogo_a_fichas(cat)[0]
    assert CANARIO_MUESTRA in f["texto"], "la versión normal usa ejemplos (mejor calidad)"
    assert CANARIO_MUESTRA not in f["texto_min"], "la versión privada NO puede llevar datos"
    assert "c (TEXT)" in f["texto_min"], "pero sí los nombres de columna"


print("\n== Generación del SQL: qué viaja según el modo ==")


@test("el prompt de generación lleva la pregunta y los nombres de tablas/columnas")
def _():
    m, llamadas = armar_motor()
    m.responder("total de saldo por cliente")
    gen = llamadas[0]
    assert "clientes" in gen["system"] and "saldo" in gen["system"]
    assert "total de saldo por cliente" in gen["user"]


@test("modo NORMAL: los valores de ejemplo del esquema SÍ viajan (hay que declararlo)")
def _():
    # DOCUMENTA la realidad, no la celebra: en modo normal, catalogo_a_fichas
    # mete unos pocos valores reales de las columnas de texto en el prompt de
    # generación, para mejor calidad. La landing tiene que decirlo así. Si
    # esto cambia, el test avisa para actualizar el texto público.
    m, llamadas = armar_motor()
    m.responder("total de saldo")
    assert CANARIO_MUESTRA in llamadas[0]["system"], \
        "en modo normal el ejemplo de columna viaja (es lo declarado)"


print("\n== Modo privacidad estricta: NI ejemplos NI filas ==")


@test("modo PRIVADO: el valor de ejemplo del esquema NO viaja en la generación")
def _():
    # El bug real que la auditoría encontró: antes esto viajaba SIEMPRE.
    m, llamadas = armar_motor()
    m.responder("total de saldo", privado=True)
    assert CANARIO_MUESTRA not in llamadas[0]["system"], \
        "en modo privado ningún dato real de la base puede viajar, ni al generar"
    assert "saldo" in llamadas[0]["system"], "pero los nombres de columna sí"


@test("modo PRIVADO: exactamente UNA llamada, sin análisis, pero la tabla vuelve entera")
def _():
    m, llamadas = armar_motor()
    r = m.responder("total de saldo", privado=True)
    assert len(llamadas) == 1, f"hubo {len(llamadas)} llamadas, se esperaba 1"
    assert r["explicacion"] is None
    assert r["filas"] == [list(FILA_1), list(FILA_2)], \
        "la privacidad no recorta el resultado: la tabla vuelve completa"


@test("modo PRIVADO: ninguna fila del resultado viaja en NINGÚN prompt")
def _():
    m, llamadas = armar_motor()
    m.responder("total de saldo", privado=True)
    for i, ll in enumerate(llamadas):
        for c in CENTINELAS_FILA:
            assert c not in ll["system"] and c not in ll["user"], \
                f"llamada {i}: se filtró la fila {c!r}"


print("\n== Análisis escrito (modo normal): qué viaja exactamente ==")


@test("la muestra del resultado SÍ viaja en la 2ª llamada (esto es lo que hay que declarar)")
def _():
    m, llamadas = armar_motor()
    r = m.responder("total de saldo")
    assert len(llamadas) == 2
    assert r["explicacion"], "en modo normal tiene que haber análisis"
    assert any(c in llamadas[1]["user"] for c in CENTINELAS_FILA), \
        "se esperaba la muestra del resultado en el prompt del análisis"


@test("la muestra está acotada a 20 filas (el 'hasta 20 filas' de la landing)")
def _():
    cols = ["nombre", "saldo"]
    filas = [[f"cliente_{i}", i] for i in range(100)]
    texto = motor._muestra_texto(cols, filas)
    assert "cliente_19" in texto, "las primeras 20 filas van"
    assert "cliente_20" not in texto, "la fila 21 NO puede viajar"
    assert "80 filas más" in texto, "debe declarar cuántas quedaron afuera"


@test("si la consulta falló (sin filas), no hay 2ª llamada aunque el análisis esté activo")
def _():
    m, llamadas = armar_motor()

    def ejecutar_roto(sql, limite=5000, params=None):
        raise RuntimeError("tabla bloqueada")

    m.cx.ejecutar = ejecutar_roto
    r = m.responder("total de saldo")
    assert r["error"], "el error tiene que reportarse"
    assert len(llamadas) == 1, "sin resultado no hay nada para explicar ni mandar"


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
