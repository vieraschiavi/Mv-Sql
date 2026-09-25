# © 2026 Martín Viera. Todos los derechos reservados.

"""Sin tope de filas por defecto. Correr: python3 tests/test_sin_tope_filas.py

Pedido del dueño: «¿Hay límite de filas? ... debe ser sin límite de tamaño
cada módulo». Lo que fija este archivo:

- `ConexionBD.ejecutar(sql, limite=None)` o `limite=0` trae TODAS las filas
  y no le agrega TOP/LIMIT al SQL. `limite=100` trae 100.
- Si un tope explícito recorta, queda anotado con el TOTAL REAL (nunca un
  recorte mudo).
- El administrador y el modo abierto (el dueño) no tienen tope. Los topes de
  analista/lector siguen, pero son editables.
- La barrera de solo lectura vale igual sin tope.
- El Excel y el CSV exportados llevan todas las filas.
"""
import io
import os
import sqlite3
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

import conectores  # noqa: E402
import equipo  # noqa: E402
import exportar  # noqa: E402
from conectores import ConexionBD, SQLNoPermitido  # noqa: E402

_tmp = tempfile.mkdtemp()
equipo.RUTA = os.path.join(_tmp, "equipo.json")

FILAS = 10_000
_DB = os.path.join(_tmp, "ventas.db")
_cx = sqlite3.connect(_DB)
_cx.execute("CREATE TABLE ventas (id INTEGER PRIMARY KEY, cliente TEXT, monto REAL)")
_cx.executemany("INSERT INTO ventas VALUES (?,?,?)",
                [(i, f"Cliente {i % 97}", float(i % 500)) for i in range(1, FILAS + 1)])
_cx.commit()
_cx.close()

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


def _conexion():
    return ConexionBD("sqlite", ruta=_DB).conectar()


print("\n== Sin tope de filas por defecto ==")


@test("limite=None trae las 10.000 filas y no agrega LIMIT")
def _():
    cx = _conexion()
    cols, filas, sql = cx.ejecutar("SELECT * FROM ventas", limite=None)
    assert len(filas) == FILAS, len(filas)
    assert "limit" not in sql.lower(), sql
    assert cx.ultimo_recorte["recortado"] is False


@test("limite=0 también es «sin tope»: las 10.000 filas")
def _():
    cx = _conexion()
    _, filas, sql = cx.ejecutar("SELECT * FROM ventas", limite=0)
    assert len(filas) == FILAS, len(filas)
    assert "limit" not in sql.lower(), sql


@test("un CTE sin tope también trae todo")
def _():
    cx = _conexion()
    _, filas, _ = cx.ejecutar(
        "WITH v AS (SELECT id, monto FROM ventas) SELECT id, monto FROM v",
        limite=None)
    assert len(filas) == FILAS, len(filas)


@test("limite=100 trae 100 y avisa con el total real")
def _():
    cx = _conexion()
    _, filas, _ = cx.ejecutar("SELECT * FROM ventas", limite=100)
    assert len(filas) == 100, len(filas)
    r = cx.ultimo_recorte
    assert r["recortado"] is True and r["tope"] == 100, r
    assert r["total"] == FILAS, r


@test("un tope que no recorta no avisa")
def _():
    cx = _conexion()
    _, filas, _ = cx.ejecutar("SELECT * FROM ventas WHERE id <= 50", limite=100)
    assert len(filas) == 50
    assert cx.ultimo_recorte["recortado"] is False


@test("el total real se cuenta también con un CTE y comentario final")
def _():
    cx = _conexion()
    _, filas, _ = cx.ejecutar(
        "WITH v AS (SELECT * FROM ventas) SELECT * FROM v -- todas", limite=10)
    assert len(filas) == 10
    assert cx.ultimo_recorte["total"] == FILAS, cx.ultimo_recorte


@test("la barrera de solo lectura vale igual sin tope")
def _():
    cx = _conexion()
    for sql in ("DELETE FROM ventas", "SELECT 1; DROP TABLE ventas",
                "UPDATE ventas SET monto = 0"):
        for limite in (None, 0):
            try:
                cx.ejecutar(sql, limite=limite)
                raise AssertionError(f"dejó pasar: {sql}")
            except SQLNoPermitido:
                pass
    _, filas, _ = cx.ejecutar("SELECT COUNT(*) FROM ventas", limite=None)
    assert filas[0][0] == FILAS, "la tabla cambió"


@test("tope_filas normaliza None/0/negativo/basura a «sin tope»")
def _():
    for v in (None, 0, "0", -5, "", "abc"):
        assert conectores.tope_filas(v) is None, v
    assert conectores.tope_filas(2000) == 2000


@test("el admin y el modo abierto no tienen tope; lector y analista sí")
def _():
    assert equipo.ROLES["admin"]["limite_filas"] == 0
    assert equipo.permisos(None)["limite_filas"] == 0
    assert equipo.ROLES["analista"]["limite_filas"] == 20000
    assert equipo.ROLES["lector"]["limite_filas"] == 2000


@test("los topes de los roles son editables y 0 = sin tope")
def _():
    equipo.crear_usuario("Dueno", "admin", "1234")
    equipo.crear_usuario("Lea", "lector", "5678")
    lea = equipo.autenticar("Lea", "5678")
    assert equipo.permisos(lea)["limite_filas"] == 2000
    equipo.fijar_limite_filas("lector", 5000)
    assert equipo.permisos(lea)["limite_filas"] == 5000
    equipo.fijar_limite_filas("lector", 0)
    assert equipo.permisos(lea)["limite_filas"] == 0
    dueno = equipo.autenticar("Dueno", "1234")
    assert equipo.permisos(dueno)["limite_filas"] == 0
    for malo in (-1, "diez"):
        try:
            equipo.fijar_limite_filas("lector", malo)
            raise AssertionError(f"aceptó {malo!r}")
        except ValueError:
            pass
    try:
        equipo.fijar_limite_filas("jefe", 10)
        raise AssertionError("aceptó un rol inexistente")
    except ValueError:
        pass


@test("app.py no vuelve a poner 5000 como tope por defecto")
def _():
    with open(os.path.join(os.path.dirname(AQUI), "app.py"), encoding="utf-8") as f:
        fuente = f.read()
    assert 'limite_filas", 5000' not in fuente
    assert "limite=5000" not in fuente


@test("el CSV exportado lleva todas las filas")
def _():
    try:
        import pandas as pd
    except ImportError:
        print("      (pandas no instalado: se saltea)")
        return
    cx = _conexion()
    cols, filas, _ = cx.ejecutar("SELECT * FROM ventas", limite=None)
    df = pd.DataFrame(filas, columns=cols)
    leido = pd.read_csv(io.BytesIO(exportar.a_csv(df)), encoding="utf-8-sig")
    assert len(leido) == FILAS, len(leido)


@test("el Excel exportado lleva todas las filas (y reparte en hojas si no entran)")
def _():
    try:
        import pandas as pd
        import openpyxl  # noqa: F401 - a_excel lo necesita
    except ImportError:
        print("      (pandas/openpyxl no instalado: se saltea)")
        return
    cx = _conexion()
    cols, filas, _ = cx.ejecutar("SELECT * FROM ventas", limite=None)
    df = pd.DataFrame(filas, columns=cols)
    hojas = pd.read_excel(io.BytesIO(exportar.a_excel(df)), sheet_name=None, header=1)
    assert len(hojas["Resultado"]) == FILAS, len(hojas["Resultado"])
    # Reparto: se achica la hoja para no generar un Excel de un millón de filas.
    original = exportar.FILAS_POR_HOJA_EXCEL
    exportar.FILAS_POR_HOJA_EXCEL = 3_000
    try:
        hojas = pd.read_excel(io.BytesIO(exportar.a_excel(df)), sheet_name=None, header=1)
    finally:
        exportar.FILAS_POR_HOJA_EXCEL = original
    partes = [k for k in hojas if k.startswith("Resultado")]
    assert partes == ["Resultado", "Resultado_2", "Resultado_3", "Resultado_4"], partes
    assert sum(len(hojas[k]) for k in partes) == FILAS


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
