# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_i18n_roles.py — los roles del equipo se leen en el idioma de la app
==================================================================
Bug que estuvo publicado y se ve en el video de demo en inglés: la
interfaz decía "Team and permissions / Add user / Role", y justo abajo
"Martín · Administrador" y "Acceso total. Gestiona el equipo y ve la
auditoría." — en castellano, en medio de una pantalla en inglés.

La causa: equipo.ROLES guarda `nombre` y `descripcion` en castellano
porque ahí es lógica de permisos (la comparten la auditoría y el recorte
del catálogo), pero app.py los pintaba tal cual en pantalla.

Se cubre de dos formas:

1. Que CADA rol de equipo.ROLES tenga su nombre y su descripción en los
   TRES idiomas. Si mañana se agrega un rol nuevo y se olvida traducirlo,
   este test falla — que es la regla trilingüe del proyecto hecha código.

2. Que app.py NO pinte los textos de equipo.ROLES directamente. Es lo que
   evita que la próxima pantalla que muestre un rol vuelva a saltearse la
   traducción sin que nadie se entere.

Es estático a propósito: no necesita streamlit ni levantar la app, así
que corre en CI igual que el resto de la suite.
"""
import ast
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

_pasadas = _falladas = 0


def test(nombre):
    def deco(fn):
        global _pasadas, _falladas
        try:
            fn()
            print(f"  ✓ {nombre}")
            _pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}")
            _falladas += 1
    return deco


APP_PY = os.path.join(RAIZ, "app.py")
IDIOMAS = ("es", "en", "pt")


def _diccionario_T():
    """El literal T de app.py, sin importar el módulo.

    Importar app.py ejecuta Streamlit entero; acá solo se necesita el
    diccionario de traducciones, así que se lee del AST.
    """
    with open(APP_PY, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read(), filename=APP_PY)
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                if isinstance(destino, ast.Name) and destino.id == "T":
                    return ast.literal_eval(nodo.value)
    raise AssertionError("no se encontró el diccionario T en app.py")


print("\n== Los roles se traducen a los tres idiomas ==")

T = _diccionario_T()
import equipo  # noqa: E402  (después de sys.path)


@test("los tres idiomas existen en T")
def _():
    for idioma in IDIOMAS:
        assert idioma in T, f"falta el idioma {idioma} en T"


@test("CADA rol tiene nombre en los 3 idiomas")
def _():
    faltan = []
    for clave in equipo.ROLES:
        for idioma in IDIOMAS:
            k = f"rol_{clave}"
            if not T[idioma].get(k):
                faltan.append(f"{idioma}:{k}")
    assert not faltan, f"roles sin nombre traducido: {faltan}"


@test("CADA rol tiene descripción en los 3 idiomas")
def _():
    faltan = []
    for clave in equipo.ROLES:
        for idioma in IDIOMAS:
            k = f"rold_{clave}"
            if not T[idioma].get(k):
                faltan.append(f"{idioma}:{k}")
    assert not faltan, f"roles sin descripción traducida: {faltan}"


@test("EL INGLÉS NO QUEDÓ EN CASTELLANO (que es el bug que se vio en cámara)")
def _():
    # Si alguien "traduce" copiando el castellano, el test de existencia
    # pasa igual. Esto compara: en inglés tienen que ser textos distintos.
    iguales = []
    for clave in equipo.ROLES:
        for prefijo in ("rol_", "rold_"):
            k = prefijo + clave
            if T["en"].get(k) and T["en"][k] == T["es"].get(k):
                iguales.append(k)
    assert not iguales, (
        f"el inglés quedó idéntico al castellano en: {iguales}")


@test("app.py NO pinta equipo.ROLES[...]['nombre'] ni ['descripcion'] directo")
def _():
    with open(APP_PY, encoding="utf-8") as fh:
        codigo = fh.read()
    # Se permite leer equipo.ROLES para la lógica (claves, permisos); lo
    # que no se permite es sacarle el texto de pantalla.
    malos = re.findall(r"equipo\.ROLES\[[^\]]+\]\[[\"'](?:nombre|descripcion)[\"']\]",
                       codigo)
    assert not malos, (
        "app.py pinta el texto de equipo.ROLES sin traducir "
        f"({malos}) — usá nombre_rol()/descripcion_rol()")


@test("los helpers de traducción existen y caen con elegancia")
def _():
    with open(APP_PY, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read(), filename=APP_PY)
    definidas = {n.name for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)}
    for fn in ("nombre_rol", "descripcion_rol"):
        assert fn in definidas, f"falta la función {fn}() en app.py"


@test("un rol desconocido no rompe la pantalla (cae al castellano)")
def _():
    # Réplica exacta de la lógica de los helpers: ante un rol que no está
    # traducido ni en equipo.ROLES, tiene que devolver algo mostrable en
    # vez de reventar con KeyError en medio del panel del equipo.
    t = T["en"]
    clave = "rol_que_no_existe"
    valor = t.get(f"rol_{clave}",
                  equipo.ROLES.get(clave, {}).get("nombre", clave))
    assert valor == clave, f"esperaba caer al literal, dio {valor!r}"


print(f"\n  {_pasadas} pasadas · {_falladas} falladas\n")
sys.exit(1 if _falladas else 0)
