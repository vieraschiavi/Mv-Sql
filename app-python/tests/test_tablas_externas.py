# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_tablas_externas.py — Analysis Services (el MDW) en MV SQL NLP, por la suite
==================================================================
Pedido: «debería usar también Azure Analysis Services» en el selector de Motor.
Analysis Services habla DAX, no SQL: la suite lee sus tablas y las deja en la
sesión; acá se vuelcan a una base SQLite y se consultan en SQL, solo lectura.

Se prueba:
  1. Las tablas se vuelcan a SQLite con nombres de tabla y columna válidos.
  2. Mismas tablas → misma base (no se rehace en cada pasada).
  3. `pendiente` entrega el paquete una sola vez por `ident`.
  4. La base resultante pasa por el mismo conector de solo lectura.
  5. La opción existe en el selector, con textos en ES/EN/PT.
"""
import os
import sqlite3
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

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


try:
    import pandas as pd
except ImportError:          # CI corre sin requirements: lo que necesita pandas se saltea
    pd = None

if pd is not None:
    TABLAS = {"Venta Interna": pd.DataFrame({"País": ["UY", "AR"], "Venta USD": [10.0, 20.0]}),
              "Dim Producto": pd.DataFrame({"Producto": ["A", "B"]})}

    @test("las tablas del MDW quedan como una base SQLite con nombres válidos")
    def _():
        ruta = TE.a_sqlite(TABLAS)
        con = sqlite3.connect(ruta)
        try:
            tablas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert tablas == {"venta_interna", "dim_producto"}, tablas
            cols = [r[1] for r in con.execute("PRAGMA table_info(venta_interna)")]
            assert cols == ["País", "Venta_USD"], cols
            assert con.execute("SELECT SUM(Venta_USD) FROM venta_interna").fetchone()[0] == 30.0
        finally:
            con.close()

    @test("mismas tablas → misma base")
    def _():
        assert TE.a_sqlite(TABLAS) == TE.a_sqlite(dict(TABLAS))

    @test("la base pasa por el conector de solo lectura de siempre")
    def _():
        from conectores import ConexionBD, SQLNoPermitido
        cx = ConexionBD("sqlite", ruta=TE.a_sqlite(TABLAS)).conectar()
        try:
            try:
                cx.ejecutar("DELETE FROM venta_interna")
                raise AssertionError("dejó borrar")
            except SQLNoPermitido:
                pass
        finally:
            if hasattr(cx, "cerrar"):
                cx.cerrar()


@test("sin tablas no hay base")
def _():
    try:
        TE.a_sqlite({})
        raise AssertionError("aceptó un paquete vacío")
    except ValueError:
        pass


@test("pendiente entrega cada paquete una sola vez")
def _():
    estado = {}
    assert TE.pendiente(estado) is None and not TE.hay(estado)
    estado[TE.CLAVE] = {"etiqueta": "Analysis Services · srv/modelo", "tablas": {"t": object()}, "ident": "a"}
    p = TE.pendiente(estado)
    assert p is not None and TE.hay(estado)
    TE.marcar_aplicada(estado, p)
    assert TE.pendiente(estado) is None
    estado[TE.CLAVE] = {**estado[TE.CLAVE], "ident": "b"}
    assert TE.pendiente(estado) is not None


@test("la opción está en el selector de Motor, en los tres idiomas")
def _():
    app = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    assert '["archivo", "aas"]' in app
    for clave in ("aas", "aas_hint", "aas_usar", "aas_listo"):
        import re
        assert len(re.findall(rf'^\s+"{clave}": "', app, re.M)) == 3, clave


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
