"""Verifica tools/build_cython.py. Correr: python3 tests/test_build_cython.py

build_cython.py corre en el runner de Windows del workflow de releases, y
ahi stdout se abre en cp1252. Ese detalle ya rompio un release entero:
compilo los tres .pyd bien y murio en el print que anunciaba el exito, con
un UnicodeEncodeError sobre el "check" del mensaje. Exit 1, job en rojo, y
el zip autoinstalable y el instalador NSIS nunca se subieron al Release.

Lo caro no es el bug: es el diagnostico. El traceback habla de codecs y de
charmap, asi que leyendolo parece que fallo la compilacion — cuando en
realidad los .pyd ya estaban generados y copiados. Se pierde el tiempo
mirando Cython.

Y es facil de reintroducir: todo el repo esta escrito en castellano, asi
que cualquier print nuevo con un acento o un guion largo lo trae de vuelta.
Por eso el arreglo es reconfigurar stdout/stderr a UTF-8 al importar, y por
eso este test ejecuta el script de verdad con la consola en cp1252 en vez
de revisar los mensajes uno por uno.
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
SCRIPT = os.path.join(RAIZ, "tools", "build_cython.py")

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


def _correr(*args, encoding="cp1252"):
    """Corre el script con la consola en el encoding que se pida.

    PYTHONIOENCODING es lo que usa Python para decidir el encoding de
    stdout, asi que fijarlo en cp1252 reproduce la consola de Windows sin
    necesitar una maquina Windows.
    """
    env = dict(os.environ, PYTHONIOENCODING=encoding)
    return subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, env=env, cwd=RAIZ)


print("\n== tools/build_cython.py en una consola que no es UTF-8 ==")


@test("el script existe donde el workflow lo llama")
def _():
    assert os.path.exists(SCRIPT), f"no esta {SCRIPT}"


@test("el mensaje de exito se imprime con la consola en cp1252")
def _():
    # Este es EL caso que rompio el release. No alcanza con correr
    # --limpiar: sus mensajes son ASCII y pasan igual sin el arreglo, o
    # sea que ese test daria verde con el bug puesto. Hay que ejercitar el
    # print de _compilar(), que es el que tiene el "check".
    #
    # Importar el modulo alcanza y no compila nada: _compilar() esta detras
    # de if __name__ == "__main__". Lo que se busca del import es su efecto
    # al cargarse — dejar stdout en UTF-8.
    fuente = open(SCRIPT, encoding="utf-8").read()
    mensajes = [ln.strip() for ln in fuente.splitlines()
                if ln.strip().startswith("print(") and any(ord(c) > 127 for c in ln)]
    assert mensajes, "no quedan prints con acentos: ¿se reescribieron en ASCII?"

    guion = (
        "import sys, os; sys.path.insert(0, os.path.join(%r, 'tools'));"
        "import build_cython;"
        # Los mismos caracteres que rompieron el job, por stdout y stderr.
        "print('\\u2713 Compilado:', 'motor.pyd');"
        "print('Falta Cython \\u2014 instala\\u00e1 con: pip install cython', file=sys.stderr)"
    ) % RAIZ
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, "-c", guion],
                       capture_output=True, text=True, env=env, cwd=RAIZ)
    assert "UnicodeEncodeError" not in r.stderr, (
        "vuelve el bug que rompio el release: el script compila los .pyd y "
        "despues muere avisando que le fue bien\n" + r.stderr[-400:])
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[-400:]}"


@test("--limpiar sigue corriendo entero bajo cp1252")
def _():
    r = _correr("--limpiar")
    assert r.stdout.strip(), "no imprimio nada"
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[-400:]}"


@test("reconfigura stdout Y stderr, no solo uno")
def _():
    # El mensaje de "falta Cython" sale por stderr. Si solo se reconfigura
    # stdout, ese camino sigue explotando — y es justo el que ve alguien
    # que corre el script sin las dependencias puestas.
    fuente = open(SCRIPT, encoding="utf-8").read()
    assert "sys.stderr" in fuente and "reconfigure" in fuente, \
        "stderr no se reconfigura: el aviso de 'falta Cython' puede romper"


@test("sigue andando en una consola UTF-8 normal")
def _():
    r = _correr("--limpiar", encoding="utf-8")
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stderr[-400:]}"


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
