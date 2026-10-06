# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_conector_aas.py — conectarse a Azure Analysis Services desde la barra lateral
==================================================================
Pedido: «tiene que permitir la conexión» (Motor = Azure Analysis Services / MDW
mostraba sólo un texto y «Conectá una base de datos en la barra lateral»).

Se prueba, con un conector de Analysis Services de mentira (acá no hay MDW):
  1. Faltan servidor, modelo, usuario/clave o token → se dice cuál, sin conectar.
  2. Usuario y contraseña se pasan al conector; la ventana (MFA) también.
  3. Se leen sólo las tablas elegidas, con el tope por tabla.
  4. Lo leído queda como base SQLite de solo lectura.
  5. Faltan pythonnet/pyadomd → se dice qué falta.
  6. Suelto (sin la suite) → se explica cómo conectarse.
  7. La barra lateral tiene el formulario, con textos en ES/EN/PT.
"""
import os
import re
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

import conector_aas as C  # noqa: E402

pasadas = falladas = 0


def test(nombre):
    def deco(fn):
        global pasadas, falladas
        try:
            fn(); print(f"  ✓ {nombre}"); pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}"); falladas += 1
    return deco


SRV = "asazure://region.asazure.windows.net/servidor"

try:
    import pandas as pd
except ImportError:
    pd = None


class _ASFalso:
    def __init__(self, faltan=()):
        self.faltan, self.llamadas = list(faltan), []

    def librerias_faltantes(self):
        return self.faltan

    def diagnostico_faltantes(self, faltan):
        return "detalle"

    def usar_usuario(self, s, u="", c=""):
        self.llamadas.append(("usuario", s, u, bool(c)))

    def usar_ventana(self, s, si=True):
        self.llamadas.append(("ventana", s, si))

    def tablas_del_modelo(self, s, m, token=""):
        return ["Venta", "Producto"]

    def leer(self, s, m, token="", tablas=None, limite=None):
        self.llamadas.append(("leer", m, tablas, limite, token))
        nombres = tablas or ["Venta", "Producto"]
        datos = [types.SimpleNamespace(nombre=n, datos=pd.DataFrame({"x": [1, 2]})) for n in nombres]
        return types.SimpleNamespace(con_datos=datos, avisos=("Venta: tope",))


def _error(fn):
    try:
        fn()
    except C.ErrorAAS as e:
        return str(e)
    raise AssertionError("no avisó")


@test("faltantes: servidor, modelo, usuario/clave y token")
def _():
    AS = _ASFalso()
    assert "asazure://" in _error(lambda: C.leer("http://x", "M", AS=AS))
    assert "modelo" in _error(lambda: C.leer(SRV, "", AS=AS))
    assert "contraseña" in _error(lambda: C.leer(SRV, "M", "usuario", "a@b.com", "", AS=AS))
    assert "token" in _error(lambda: C.leer(SRV, "M", "token", AS=AS))
    assert AS.llamadas == [], "intentó conectar con datos faltantes"


@test("sin pythonnet/pyadomd se dice qué falta")
def _():
    assert "pythonnet" in _error(lambda: C.listar_tablas(SRV, "M", "ventana", AS=_ASFalso(["pythonnet"])))


@test("suelto, sin la suite, se explica cómo conectarse")
def _():
    if C.motor_suite() is None:
        assert "Adium All in One" in _error(lambda: C.listar_tablas(SRV, "M", "ventana"))


@test("lista las tablas del modelo")
def _():
    assert C.listar_tablas(SRV, "Modelo", "ventana", AS=_ASFalso()) == ["Venta", "Producto"]


if pd is not None:
    @test("usuario y contraseña, sólo las tablas elegidas y el tope")
    def _():
        AS = _ASFalso()
        et, datos, avisos = C.leer(SRV, "Modelo", "usuario", "persona@empresa.com", "clave",
                                   tablas=["Venta"], limite=500, AS=AS)
        assert ("usuario", SRV, "persona@empresa.com", True) in AS.llamadas
        assert ("ventana", SRV, False) in AS.llamadas
        assert ("leer", "Modelo", ["Venta"], 500, "") in AS.llamadas
        assert list(datos) == ["Venta"] and et == "Analysis Services · Modelo" and avisos == ["Venta: tope"]

    @test("la ventana de Microsoft no manda usuario y lo leído queda como base de solo lectura")
    def _():
        import tablas_externas
        from conectores import ConexionBD, SQLNoPermitido
        AS = _ASFalso()
        _, datos, _ = C.leer(SRV, "Modelo", "ventana", AS=AS)
        assert ("usuario", SRV, "", False) in AS.llamadas and ("ventana", SRV, True) in AS.llamadas
        cx = ConexionBD("sqlite", ruta=tablas_externas.a_sqlite(datos)).conectar()
        try:
            try:
                cx.ejecutar("DROP TABLE venta")
                raise AssertionError("dejó borrar")
            except SQLNoPermitido:
                pass
        finally:
            if hasattr(cx, "cerrar"):
                cx.cerrar()


@test("la barra lateral tiene el formulario, en los tres idiomas")
def _():
    app = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    assert "conector_aas.leer(" in app and "conector_aas.listar_tablas(" in app
    for clave in ("aas_servidor", "aas_modelo", "aas_auth", "aas_usuario", "aas_clave", "aas_conectar",
                  "aas_ver_tablas", "aas_tope", "aas_auth_usuario", "aas_auth_ventana", "aas_auth_token"):
        assert len(re.findall(rf'^\s+"{clave}": "', app, re.M)) == 3, clave


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
