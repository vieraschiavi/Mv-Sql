"""
build_cython.py — compila los módulos sensibles de MV SQL NLP
==================================================================
Hasta ahora, todo lo que se distribuye (zip o instalador .exe) es
Python plano: quien tiene la demo puede abrir motor.py con Claude y
leer exactamente cómo se arma el prompt, cómo se valida el SQL, cómo
funciona el trial. Este script compila esos módulos a extensiones
binarias (.pyd en Windows, .so en Linux/Mac) con Cython — no hace
falta reescribir nada como .pyx: cythonize() compila los .py tal
cual están.

Qué se compila y por qué (MODULOS abajo):
  - motor.py          el motor NL→SQL: prompts, RAG, validación,
                       confianza — el "know-how" real del producto.
  - proveedores_ia.py el ruteo de proveedores de IA y la llamada al
                       proxy de créditos.
  - licencia.py       el trial y la verificación de licencia — que
                       esto sea binario sube el costo de parchear el
                       chequeo, no solo de leerlo.

Qué NO se compila (a propósito): app.py (es el script que corre
streamlit, más simple dejarlo fuente), y el resto de los módulos
(conectores, exportar, cuadernos, equipo, auditoria, esquema_visual,
guardadas, catalogo, eula) — son UI/IO genéricos, no hay "receta" que
proteger ahí, y compilarlos no vale el costo de build extra.

Límite honesto (mismo espíritu que licencia.py): Cython compilado NO
es inquebrantable. Un ingeniero con tiempo puede desensamblar la
extensión o usar un decompilador de Cython. Lo que sí logra es sacar
el "copiar y pegar en Claude" de la ecuación — hace falta ingeniería
reversa de verdad, no una lectura de 5 minutos. Protección real y
total del código requeriría no distribuirlo (arquitectura SaaS) — eso
es una decisión de arquitectura aparte, no algo que este script
resuelva.

Requiere un compilador de C instalado:
  - Windows: Visual C++ Build Tools (ya vienen en los runners
    windows-latest de GitHub Actions — ver .github/workflows/build-desktop.yml)
  - Linux/Mac: gcc/clang (para probar el pipeline localmente; el .so
    que generás acá NO sirve para el instalador de Windows, solo para
    verificar que la compilación y el import funcionan igual que el
    .py original)

    pip install cython
    python tools/build_cython.py            # compila in-place en app-python/
    python tools/build_cython.py --limpiar   # borra los artefactos de build
==================================================================
"""
import glob
import os
import shutil
import sys

# La consola de Windows abre stdout en cp1252, que no sabe escribir ni el
# "✓" ni el guión largo ni los acentos — y este archivo, como todo el
# repo, está en castellano. Sin esto, el script compila los tres módulos
# bien y recién MUERE al imprimir que le fue bien: UnicodeEncodeError en
# el print final, exit 1, y el job de release se cae con los .pyd ya
# generados. Pasó de verdad en el runner (run #3), y el error no dice
# nada sobre encodings a primera vista: parece que falló la compilación.
#
# Se arregla acá y no sacando los acentos de cada print porque lo segundo
# hay que acordárselo cada vez que alguien agrega un mensaje.
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APP_PYTHON = os.path.join(RAIZ, "app-python")

MODULOS = ["motor.py", "proveedores_ia.py", "licencia.py"]

# Extensiones compiladas que puede dejar atrás un build (por módulo y
# plataforma): se usan tanto para ubicar el resultado como para poder
# limpiar sin dejar basura.
_PATRONES_COMPILADOS = ("*.pyd", "*.so")


def _limpiar():
    borrados = []
    for nombre in MODULOS:
        base = nombre[:-3]  # sin ".py"
        for patron in _PATRONES_COMPILADOS:
            ext = patron[1:]  # ".pyd" / ".so"
            for ruta in glob.glob(os.path.join(APP_PYTHON, f"{base}*{ext}")):
                os.remove(ruta)
                borrados.append(os.path.basename(ruta))
    for carpeta in ("build",):
        ruta = os.path.join(APP_PYTHON, carpeta)
        if os.path.isdir(ruta):
            shutil.rmtree(ruta)
            borrados.append(f"{carpeta}/")
    for ruta in glob.glob(os.path.join(APP_PYTHON, "*.c")):
        # Cython genera un .c intermedio por módulo compilado — no hace
        # falta distribuirlo, solo sirve para el build.
        if os.path.splitext(os.path.basename(ruta))[0] in {m[:-3] for m in MODULOS}:
            os.remove(ruta)
            borrados.append(os.path.basename(ruta))
    print("Limpiado:", ", ".join(borrados) if borrados else "(nada para limpiar)")


def _compilar():
    try:
        from Cython.Build import cythonize
    except ImportError:
        print("Falta Cython — instalá con: pip install cython", file=sys.stderr)
        sys.exit(1)
    from setuptools import setup

    rutas = [os.path.join(APP_PYTHON, m) for m in MODULOS]
    faltantes = [r for r in rutas if not os.path.exists(r)]
    if faltantes:
        print("No se encontraron:", ", ".join(faltantes), file=sys.stderr)
        sys.exit(1)

    cwd_original = os.getcwd()
    os.chdir(APP_PYTHON)
    try:
        setup(
            script_name="setup.py",
            script_args=["build_ext", "--inplace"],
            ext_modules=cythonize(
                MODULOS,
                compiler_directives={"language_level": "3", "binding": True},
                # Sin esto Cython no sabe de dónde vienen los .py (estamos
                # llamándolo con cwd=APP_PYTHON, no desde la raíz del repo).
                build_dir="build",
            ),
        )
    finally:
        os.chdir(cwd_original)

    generados = []
    for m in MODULOS:
        base = m[:-3]
        encontrados = glob.glob(os.path.join(APP_PYTHON, f"{base}*.pyd")) + \
            glob.glob(os.path.join(APP_PYTHON, f"{base}*.so"))
        generados.extend(os.path.basename(g) for g in encontrados)

    print()
    print("✓ Compilado:", ", ".join(generados) if generados else "(nada — revisar errores arriba)")
    if any(g.endswith(".so") for g in generados):
        print("  (.so — sirve para probar el pipeline en Linux/Mac, NO para el instalador")
        print("   de Windows. El release real se compila en CI sobre windows-latest.)")


if __name__ == "__main__":
    if "--limpiar" in sys.argv:
        _limpiar()
    else:
        _compilar()
