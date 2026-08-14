# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_generador_owner.py — el conversor a version propietario se genera
bien y con la licencia real, sin corromper el resto del script.
==================================================================
tools/generar_conversor_owner.py toma owner/plantilla-convertir-a-dueno.ps1
(commiteada, SIN licencia real — solo el marcador @@LICENCIA_OWNER_JSON@@)
y produce owner/dist/convertir-a-version-dueno.ps1 CON la licencia real
adentro. Ese archivo generado nunca se commitea (está en .gitignore):
si se filtrara, cualquiera que lo corra se convierte en "propietario"
sin pagar, porque el chequeo del lado del cliente (licencia.py,
licencia.cjs) solo mira la fecha "vence" — no hay firma que verificar.

El bug real que motiva este test: el marcador aparece DOS veces en la
plantilla — una en la asignación de PowerShell (código) y otra en el
comentario que la explica (prosa). Un str.replace() ingenuo reemplaza
las dos, y la segunda queda con un bloque de JSON incrustado a mitad de
una oración — el script sigue "funcionando" pero el comentario que
explica el mecanismo de seguridad queda ilegible. Nada revienta, así
que sin este test el problema pasa desapercibido.
"""
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
SCRIPT = os.path.join(RAIZ, "tools", "generar_conversor_owner.py")
PLANTILLA = os.path.join(RAIZ, "owner", "plantilla-convertir-a-dueno.ps1")
SALIDA = os.path.join(RAIZ, "owner", "dist")
PS1_GENERADO = os.path.join(SALIDA, "convertir-a-version-dueno.ps1")
BAT_GENERADO = os.path.join(SALIDA, "Convertir-a-version-dueno.bat")

_python = sys.executable

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


def limpiar_salida():
    import shutil
    if os.path.exists(SALIDA):
        shutil.rmtree(SALIDA)


def correr_generador():
    return subprocess.run([_python, SCRIPT], cwd=RAIZ, capture_output=True, text=True)


print("\n== El conversor a version propietario se genera bien ==")


@test("la plantilla existe y trae el marcador SIN licencia real")
def _():
    assert os.path.exists(PLANTILLA), "falta owner/plantilla-convertir-a-dueno.ps1"
    texto = open(PLANTILLA, encoding="utf-8").read()
    assert "@@LICENCIA_OWNER_JSON@@" in texto, \
        "la plantilla commiteada no tiene el marcador: ¿tiene una licencia real adentro?"
    assert '"vence":"2099' not in texto.replace(" ", ""), \
        "LA PLANTILLA COMMITEADA TIENE UNA LICENCIA REAL ADENTRO — esto no puede llegar a git"


@test("el generador corre limpio y produce los dos archivos")
def _():
    limpiar_salida()
    try:
        r = correr_generador()
        assert r.returncode == 0, f"salió con código {r.returncode}: {r.stdout}\n{r.stderr}"
        assert os.path.exists(PS1_GENERADO), "no generó el .ps1"
        assert os.path.exists(BAT_GENERADO), "no generó el .bat"
    finally:
        pass  # los siguientes tests reusan esta salida


@test("el .ps1 generado lleva una licencia real (vence 2099), no el marcador")
def _():
    texto = open(PS1_GENERADO, encoding="utf-8").read()
    assert "@@LICENCIA_OWNER_JSON@@" not in texto.split("\n")[
        [i for i, l in enumerate(texto.split("\n")) if l.startswith("$LicenciaOwner")][0]
    ], "la línea de código sigue con el marcador sin reemplazar"

    m = re.search(r"\$LicenciaOwner = '(\{.*\})'", texto)
    assert m, "no se encontró la asignación $LicenciaOwner en el .ps1 generado"
    licencia = json.loads(m.group(1))  # tiene que ser JSON válido de verdad
    assert licencia.get("vence", "").startswith("2099"), \
        f"la licencia generada no vence en 2099: {licencia.get('vence')}"
    assert licencia.get("producto") == "MV SQL NLP"


@test("EL COMENTARIO QUE EXPLICA EL MARCADOR NO SE CORROMPE (el bug real)")
def _():
    # Antes de la corrección, el .replace() global pisaba TAMBIÉN la
    # mención del marcador dentro de la prosa del comentario, dejando un
    # bloque de JSON a mitad de una oración. La plantilla y el generado
    # tienen que ser IDÉNTICOS salvo esa única línea de código.
    plantilla_lineas = open(PLANTILLA, encoding="utf-8").read().splitlines()
    generado_lineas = open(PS1_GENERADO, encoding="utf-8").read().splitlines()
    assert len(plantilla_lineas) == len(generado_lineas), \
        "el generado tiene distinta cantidad de líneas que la plantilla"

    diffs = [i for i, (a, b) in enumerate(zip(plantilla_lineas, generado_lineas)) if a != b]
    assert diffs == [i for i, l in enumerate(plantilla_lineas) if l.startswith("$LicenciaOwner")], \
        f"cambiaron líneas que no debían: {diffs}"

    # Y puntualmente, la línea del comentario sigue mencionando el
    # marcador tal cual, sin JSON incrustado.
    comentario = [l for l in generado_lineas if "el marcador" in l]
    assert comentario, "no se encontró la línea del comentario que explica el marcador"
    assert "@@LICENCIA_OWNER_JSON@@" in comentario[0], \
        f"el comentario quedó corrompido: {comentario[0][:150]}"


@test("owner/dist/ está en .gitignore (si no, el .ps1 con la licencia real se commitea)")
def _():
    r = subprocess.run(["git", "check-ignore", "owner/dist/convertir-a-version-dueno.ps1"],
                       cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, \
        "owner/dist/ NO está ignorado por git: el .ps1 con la licencia real podría commitearse"


@test("una plantilla sin el marcador de código corta con error, no genera nada a medias")
def _():
    import tempfile
    limpiar_salida()
    with tempfile.TemporaryDirectory() as tmp:
        plantilla_rota = os.path.join(tmp, "plantilla-convertir-a-dueno.ps1")
        with open(plantilla_rota, "w", encoding="utf-8") as fh:
            fh.write("# sin marcador de ningún tipo\n")
        script_tmp = os.path.join(tmp, "generar_conversor_owner.py")
        # Se corre el script real pero apuntado a una plantilla rota, para
        # no tener que reescribir la de verdad y arriesgarse a dejarla mal.
        src = open(SCRIPT, encoding="utf-8").read()
        src_apuntado = src.replace(
            'PLANTILLA = os.path.join(RAIZ, "owner", "plantilla-convertir-a-dueno.ps1")',
            f'PLANTILLA = {plantilla_rota!r}')
        with open(script_tmp, "w", encoding="utf-8") as fh:
            fh.write(src_apuntado)
        r = subprocess.run([_python, script_tmp], cwd=RAIZ, capture_output=True, text=True)
        assert r.returncode != 0, "una plantilla sin marcador no debería generar nada"
    assert not os.path.exists(PS1_GENERADO), "generó un .ps1 a partir de una plantilla rota"


limpiar_salida()  # no dejar owner/dist/ generado al terminar los tests

print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
