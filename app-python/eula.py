"""
eula.py — aceptación del EULA de MV SQL NLP
==================================================================
Antes de este módulo, el acuerdo de licencia (EULA) solo se mostraba
en la página del instalador de Windows (installer/mvsql.nsi) — quien
usaba el zip + INICIAR_MVSQL.bat nunca lo veía ni lo aceptaba. Esto lo
hace cumplir para cualquier forma de instalación: la app no arranca
hasta que se acepta, una sola vez por PC.

Los textos (EULA_ES.txt, EULA_EN.txt, EULA_PT.txt) son copia exacta
de desktop/build/LICENSE*.txt — si el acuerdo cambia, actualizar los
dos lugares. La aceptación queda atada al hash del texto: si el EULA
cambia de contenido, la marca vieja no sirve y se vuelve a pedir.
==================================================================
"""
import hashlib
import json
import os
from datetime import datetime, timezone

_DIR_APP = os.path.dirname(os.path.abspath(__file__))
RUTA_MARCA_EULA = os.path.join(_DIR_APP, ".eula_aceptado")

_ARCHIVO_EULA = {"es": "EULA_ES.txt", "en": "EULA_EN.txt", "pt": "EULA_PT.txt"}


def texto_eula(idioma):
    ruta = os.path.join(_DIR_APP, _ARCHIVO_EULA.get(idioma, _ARCHIVO_EULA["es"]))
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _hash_eula_actual():
    """Hash de los 3 textos juntos: cualquier cambio en cualquier idioma invalida la marca."""
    h = hashlib.sha256()
    for idioma in sorted(_ARCHIVO_EULA):
        h.update(texto_eula(idioma).encode("utf-8"))
    return h.hexdigest()


def eula_aceptado():
    if not os.path.exists(RUTA_MARCA_EULA):
        return False
    try:
        with open(RUTA_MARCA_EULA, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("hash_eula") == _hash_eula_actual()
    except (json.JSONDecodeError, KeyError, OSError):
        return False


def registrar_aceptacion():
    data = {
        "hash_eula": _hash_eula_actual(),
        "aceptado": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(RUTA_MARCA_EULA, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError:
        pass  # sin permiso de escritura: se va a volver a preguntar la próxima vez
