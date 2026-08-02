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


# Valores centinela: si CUALQUIERA aparece en un prompt donde no debe,
# el test lo nombra. Son raros a propósito para que no haya coincidencias.
FILA_1 = ("ACME_CONFIDENCIAL_771", 98765.43)
FILA_2 = ("CLIENTE_RESERVADO_909", 12345.67)
CENTINELAS = [str(v) for fila in (FILA_1, FILA_2) for v in fila]

SQL_CANONICO = "SELECT nombre, saldo FROM clientes"


class RecuperadorFalso:
    def recuperar(self, pregunta, k=4):
        return ([{"tabla": "clientes",
                  "texto": "Tabla clientes: columnas id, nombre, saldo"}], [0.9])


class ConexionFalsa:
    dialecto = "sqlite"

    def ejecutar(self, sql, limite=5000):
        return (["nombre", "saldo"], [list(FILA_1), list(FILA_2)], sql)


def armar_motor():
    m = motor.MotorMVSQL.__new__(motor.MotorMVSQL)
    m.cx = ConexionFalsa()
    m.recuperador = RecuperadorFalso()
    m.catalogo = {"tablas": {"clientes": {"columnas": [
        {"columna": "id"}, {"columna": "nombre"}, {"columna": "saldo"}]}}}
    llamadas = []

    def completar_falso(system, user, max_tokens=1500):
        llamadas.append({"system": system, "user": user})
        if len(llamadas) == 1:
            return f"SQL:\n{SQL_CANONICO}\nCONFIANZA: 93\nSUPUESTOS: ninguno"
        return "El saldo total es alto y se concentra en dos clientes."

    m._completar = completar_falso
    return m, llamadas


print("\n== Generación del SQL: viaja el esquema, no los datos ==")


@test("el prompt de generación lleva la pregunta y los nombres de tablas/columnas")
def _():
    m, llamadas = armar_motor()
    m.responder("total de saldo por cliente", explicar=False)
    gen = llamadas[0]
    assert "clientes" in gen["system"] and "saldo" in gen["system"]
    assert "total de saldo por cliente" in gen["user"]


@test("ningún valor de fila aparece en el prompt de generación")
def _():
    m, llamadas = armar_motor()
    m.responder("total de saldo", explicar=True)
    gen = llamadas[0]
    for c in CENTINELAS:
        assert c not in gen["system"] and c not in gen["user"], \
            f"se filtró el valor {c!r} en la generación"


print("\n== Modo privacidad estricta (explicar=False) ==")


@test("exactamente UNA llamada a la IA, y sin explicación")
def _():
    m, llamadas = armar_motor()
    r = m.responder("total de saldo", explicar=False)
    assert len(llamadas) == 1, f"hubo {len(llamadas)} llamadas, se esperaba 1"
    assert r["explicacion"] is None
    assert r["filas"] == [list(FILA_1), list(FILA_2)], \
        "la tabla igual tiene que volver completa: la privacidad no recorta el resultado"


@test("ningún centinela viaja en NINGÚN prompt con explicar=False")
def _():
    m, llamadas = armar_motor()
    m.responder("total de saldo", explicar=False)
    for i, ll in enumerate(llamadas):
        for c in CENTINELAS:
            assert c not in ll["system"] and c not in ll["user"], \
                f"llamada {i}: se filtró {c!r}"


print("\n== Análisis escrito (explicar=True): qué viaja exactamente ==")


@test("la muestra del resultado SÍ viaja en la 2ª llamada (esto es lo que hay que declarar)")
def _():
    # Este caso DOCUMENTA el comportamiento, no lo celebra: si el análisis
    # está activado, una muestra del resultado viaja al proveedor. La landing
    # y el video tienen que decirlo así. Si alguien lo cambia (p. ej. deja de
    # mandar filas), este test avisa para actualizar el texto público.
    m, llamadas = armar_motor()
    r = m.responder("total de saldo", explicar=True)
    assert len(llamadas) == 2
    assert r["explicacion"], "con explicar=True tiene que haber análisis"
    assert any(c in llamadas[1]["user"] for c in CENTINELAS), \
        "se esperaba la muestra del resultado en el prompt del análisis"


@test("la muestra está acotada a 20 filas (el 'hasta 20 filas' de la landing)")
def _():
    cols = ["nombre", "saldo"]
    filas = [[f"cliente_{i}", i] for i in range(100)]
    texto = motor._muestra_texto(cols, filas)
    assert "cliente_19" in texto, "las primeras 20 filas van"
    assert "cliente_20" not in texto, "la fila 21 NO puede viajar"
    assert "80 filas más" in texto, "debe declarar cuántas quedaron afuera"


@test("si la consulta falló (sin filas), no hay 2ª llamada ni con explicar=True")
def _():
    m, llamadas = armar_motor()

    def ejecutar_roto(sql, limite=5000):
        raise RuntimeError("tabla bloqueada")

    m.cx.ejecutar = ejecutar_roto
    r = m.responder("total de saldo", explicar=True)
    assert r["error"], "el error tiene que reportarse"
    assert len(llamadas) == 1, "sin resultado no hay nada para explicar ni mandar"


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
