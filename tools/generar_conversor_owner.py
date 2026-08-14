# © 2026 Martín Viera. Todos los derechos reservados.

"""
generar_conversor_owner.py — genera el conversor a propietario CON la
licencia real adentro. Correr SOLO en tu máquina, nunca en CI.
==================================================================
owner/plantilla-convertir-a-dueno.ps1 se versiona sin licencia real: el
marcador @@LICENCIA_OWNER_JSON@@ no pasa el chequeo que trae el propio
script, así que si alguien lo baja del repo público y lo corre tal cual,
no escribe nada.

Este script reemplaza ese marcador por una licencia de verdad (vence
2099) y deja el resultado en owner/dist/ — carpeta en .gitignore a
propósito: si el .ps1 con la licencia real llegara a commitearse,
cualquiera que clone el repo público se convierte en "propietario" sin
pagar nada. La forma de repartirlo es copiar owner/dist/ a mano (o por
un canal privado) a la máquina donde se va a usar.

Uso: python3 tools/generar_conversor_owner.py
"""
import json
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTILLA = os.path.join(RAIZ, "owner", "plantilla-convertir-a-dueno.ps1")
BAT = os.path.join(RAIZ, "owner", "Convertir-a-version-dueno.bat")
SALIDA = os.path.join(RAIZ, "owner", "dist")
MARCADOR = "@@LICENCIA_OWNER_JSON@@"

# Misma forma que licencia_owner.json (build-desktop.yml) y el bloque
# PROPIETARIO de installer/mvsql.nsi: los tres lectores (licencia.cjs,
# licencia.py y motor.py) sólo miran "vence" — no valen los demás campos,
# pero se completan igual porque es la misma forma que ve un cliente real.
LICENCIA = {
    "producto": "MV SQL NLP",
    "email": "propietario@mvsqlnlp.com",
    "plan": "propietario",
    "modo": "propietario",
    "emitida": "2026-01-01T00:00:00+00:00",
    "vence": "2099-12-31T00:00:00+00:00",
    "nota": "Versión del propietario: sin límite de prueba.",
}


def main():
    if not os.path.exists(PLANTILLA):
        sys.exit(f"No se encontró la plantilla: {PLANTILLA}")
    if not os.path.exists(BAT):
        sys.exit(f"No se encontró el .bat de entrada: {BAT}")

    texto = open(PLANTILLA, "r", encoding="utf-8").read()
    # El marcador aparece DOS veces en la plantilla: una vez en la
    # asignación de PowerShell ($LicenciaOwner = '@@...@@') y otra en el
    # comentario que la explica. Un .replace() ingenuo pisa las dos, y la
    # segunda queda con un bloque de JSON incrustado a mitad de una
    # oración. Por eso se reemplaza solo la ocurrencia ENTRE COMILLAS
    # SIMPLES — la única que es código de verdad.
    objetivo = f"'{MARCADOR}'"
    if objetivo not in texto:
        sys.exit(f"La plantilla no tiene la asignación {objetivo} — no se genera nada.")

    # json.dumps con comillas dobles: nunca produce un apóstrofe que
    # rompería las comillas simples de PowerShell que rodean al marcador.
    licencia_json = json.dumps(LICENCIA, ensure_ascii=False, separators=(",", ":"))
    if "'" in licencia_json:
        sys.exit("La licencia generada contiene un apóstrofe: rompería el .ps1. Revisar LICENCIA.")

    generado = texto.replace(objetivo, f"'{licencia_json}'")
    # El marcador SIGUE apareciendo una vez más: la mención en el
    # comentario que lo explica, que no se toca a propósito. Lo que no
    # puede quedar es la asignación de código sin reemplazar.
    if objetivo in generado:
        sys.exit("La asignación de código sigue con el marcador sin reemplazar — revisar la plantilla a mano.")

    os.makedirs(SALIDA, exist_ok=True)
    destino_ps1 = os.path.join(SALIDA, "convertir-a-version-dueno.ps1")
    # CRLF: PowerShell en Windows lo tolera igual con LF, pero Notepad y
    # algunos antivirus corporativos leen mal un .ps1 solo-LF.
    with open(destino_ps1, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(generado)
    shutil.copy(BAT, os.path.join(SALIDA, "Convertir-a-version-dueno.bat"))

    print(f"Generado en: {SALIDA}")
    print("  - convertir-a-version-dueno.ps1  (CON la licencia real — no subir a ningún lado público)")
    print("  - Convertir-a-version-dueno.bat")
    print()
    print("Copiá los dos archivos a la PC donde instalaste MV SQL NLP (Python y/o")
    print("Electron, cualquiera de los dos o los dos) y corré el .bat. No hace falta")
    print("administrador ni saber dónde quedó instalado — el script lo busca solo.")


if __name__ == "__main__":
    main()
