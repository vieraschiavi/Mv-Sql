# © 2026 Martín Viera. Todos los derechos reservados.

"""Intervalo de confianza y «unidades Y moneda». Correr: python3 tests/test_confianza_medidas.py

Dos quejas reales del dueño, con el dataset de Bases y condiciones:

  - El RAG marcaba 25 con el SQL correcto: la señal era sólo similitud
    TF-IDF entre la pregunta y la ficha, y «ventas en unidades y dólares»
    contra una columna `VentasUSD` da ~0.08. Ahora cuenta la cobertura real
    (¿las tablas del SQL son las que el RAG trajo?) y lo que pasó al
    ejecutar.
  - Pidió unidades y moneda por separado y el resultado traía una sola.
    Ahora se detecta, se reintenta pidiendo una columna por medida y, si
    igual falta, se avisa y la confianza baja.
"""
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

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


CAT = {"tablas": {"mercado": {"n_filas": 3, "columnas": [
    {"columna": "Medico", "tipo": "TEXT", "pk": False, "nullable": True},
    {"columna": "Unidades", "tipo": "REAL", "pk": False, "nullable": True},
    {"columna": "VentasUSD", "tipo": "REAL", "pk": False, "nullable": True},
]}}, "fks": [], "joins_inferidos": {}}
PREGUNTA = "ventas por médico en unidades y en dólares"
SQL_UNA = "SELECT Medico, SUM(VentasUSD) AS total_usd FROM mercado GROUP BY Medico"
SQL_DOS = ("SELECT Medico, SUM(Unidades) AS total_unidades, "
           "SUM(VentasUSD) AS total_monto_usd FROM mercado GROUP BY Medico")


class Cx:
    dialecto = "sqlite"

    def __init__(self, falla=False):
        self.falla = falla

    def ejecutar(self, sql, limite=5000, params=None):
        if self.falla:
            raise RuntimeError("no such column")
        if "Unidades" in sql:
            return (["Medico", "total_unidades", "total_monto_usd"],
                    [["A", 10, 100.0]], sql)
        return (["Medico", "total_usd"], [["A", 100.0]], sql)


def armar(respuestas, falla=False):
    m = motor.MotorMVSQL.__new__(motor.MotorMVSQL)
    m.cx = Cx(falla)
    m.catalogo = CAT
    ficha = {"tabla": "mercado", "texto": "mercado(Medico, Unidades, VentasUSD)"}

    class Rec:
        def recuperar(self, pregunta, k=4):
            return ([ficha], [0.08])          # similitud léxica baja, como en la realidad

    m.recuperador = Rec()
    llamadas = []

    def completar(system, user, max_tokens=1500):
        llamadas.append(user)
        return respuestas[min(len(llamadas) - 1, len(respuestas) - 1)]

    m._completar = completar
    return m, llamadas


def rta(sql, conf=90):
    return f"SQL:\n{sql}\nCONFIANZA: {conf}\nSUPUESTOS: ninguno"


print("\n== medidas pedidas ==")


@test("detecta que se piden unidades y moneda (ES/EN/PT)")
def _():
    assert motor.medidas_pedidas(PREGUNTA) == ["unidades", "moneda"]
    assert motor.medidas_pedidas("sales in units and USD by doctor") == ["unidades", "moneda"]
    assert motor.medidas_pedidas("vendas em quantidade e faturamento") == ["unidades", "moneda"]


@test("una sola medida no dispara nada (vacío)")
def _():
    assert motor.medidas_pedidas("ventas en dólares por médico") == []
    assert motor.medidas_pedidas("") == []


@test("reconoce qué columna es cada medida")
def _():
    assert motor.medidas_sin_columna(["unidades", "moneda"], ["Medico", "total_usd"]) == ["unidades"]
    assert motor.medidas_sin_columna(["unidades", "moneda"],
                                     ["total_unidades", "total_monto_usd"]) == []


print("\n== responder ==")


@test("si trae una sola medida, reintenta y se queda con la de dos columnas")
def _():
    m, llamadas = armar([rta(SQL_UNA), rta(SQL_DOS)])
    r = m.responder(PREGUNTA, explicar=False)
    assert len(llamadas) == 2, llamadas
    assert "POR SEPARADO" in llamadas[1]
    assert r["columnas"] == ["Medico", "total_unidades", "total_monto_usd"], r["columnas"]
    assert r["medidas_faltantes"] == []
    assert r["confianza"]["componentes"]["ejecucion"] == 100


@test("si el reintento tampoco la trae, avisa y la confianza baja")
def _():
    m, _ = armar([rta(SQL_UNA), rta(SQL_UNA)])
    r = m.responder(PREGUNTA, explicar=False)
    assert r["medidas_faltantes"] == ["unidades"]
    assert any("unidades" in a for a in r["advertencias"])
    bueno, _ = armar([rta(SQL_DOS)])
    assert r["confianza"]["puntaje"] < bueno.responder(PREGUNTA, explicar=False)["confianza"]["puntaje"]


@test("RAG: con la tabla correcta recuperada no marca 25 por la similitud léxica")
def _():
    m, _ = armar([rta(SQL_DOS)])
    c = m.responder(PREGUNTA, explicar=False)["confianza"]
    assert c["componentes"]["rag"] == 100, c
    assert c["puntaje"] >= 85, c


@test("extremo: si la consulta tira error, la confianza no puede ser alta")
def _():
    m, _ = armar([rta(SQL_DOS, conf=99)], falla=True)
    c = m.responder(PREGUNTA, explicar=False)["confianza"]
    assert c["puntaje"] <= 35 and c["componentes"]["ejecucion"] == 0, c


@test("cobertura: None si el SQL no nombra tablas del catálogo")
def _():
    assert motor.cobertura_esquema("SELECT 1", CAT, ["mercado"]) is None
    assert motor.cobertura_esquema(SQL_DOS, CAT, ["otra"]) == 0.0
    assert motor.cobertura_esquema(SQL_DOS, CAT, ["dbo.mercado"]) == 1.0


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
