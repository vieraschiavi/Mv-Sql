"""
licencia.py — trial y licencia de MV SQL NLP
==================================================================
Antes de este módulo, "prueba gratis de 7 días" era solo texto en la
web: la app, una vez descargada, corría sin límite para siempre. Acá
se hace cumplir de verdad:

  - Trial de TRIAL_DIAS días contados desde la primera vez que se
    abre la app en esta PC (marca en un archivo local).
  - Si existe una licencia paga vigente (`licencia_mvsql.json`,
    emitida por la web tras el pago — ver `web/api/download.js`),
    el trial no aplica: acceso completo mientras no venza.

Límite honesto: esto es protección del lado del cliente. Sin un
servidor que la app consulte en cada arranque (que hoy no existe:
ver `docs/PLAN_DE_NEGOCIO.md`, sección de riesgos), un usuario técnico
decidido puede borrar el archivo de marca para reiniciar el trial.
Lo que sí se detecta es el truco más común (adelantar el reloj del
sistema) y la edición a mano del archivo (invalida la firma y reinicia
el trial en vez de extenderlo). Volverlo infalsificable requiere mover
la verificación a un servidor propio — ver conversación sobre SaaS.
==================================================================
"""
import hashlib
import json
import os
from datetime import datetime, timezone

TRIAL_DIAS = 7

# No es una clave criptográfica secreta (vive en el mismo archivo que se
# quiere proteger, así que cualquiera puede leerla) — solo evita que
# editar la fecha a mano "a ojo" alargue el trial sin que se note: si no
# coincide la firma, se descarta el archivo y arranca un trial nuevo.
_SAL = "mvsql-nlp-trial-v1"

_DIR_APP = os.path.dirname(os.path.abspath(__file__))
RUTA_MARCA_TRIAL = os.path.join(_DIR_APP, ".mvsql_trial.json")
RUTA_LICENCIA = os.path.join(_DIR_APP, "licencia_mvsql.json")


def _firma(inicio_iso):
    return hashlib.sha256((_SAL + inicio_iso).encode("utf-8")).hexdigest()


def _leer_marca_trial():
    if not os.path.exists(RUTA_MARCA_TRIAL):
        return None
    try:
        with open(RUTA_MARCA_TRIAL, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        inicio = data.get("inicio", "")
        if data.get("firma") != _firma(inicio):
            return None
        return inicio
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _crear_marca_trial():
    inicio = datetime.now(timezone.utc).isoformat()
    try:
        with open(RUTA_MARCA_TRIAL, "w", encoding="utf-8") as fh:
            json.dump({"inicio": inicio, "firma": _firma(inicio)}, fh)
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(RUTA_MARCA_TRIAL, 2)  # oculto
            except Exception:
                pass
    except OSError:
        pass  # sin permiso de escritura: sigue funcionando, solo no persiste entre arranques
    return inicio


def _licencia_vigente():
    """True si hay una licencia paga (own_ai o credits) con vencimiento futuro."""
    if not os.path.exists(RUTA_LICENCIA):
        return False
    try:
        with open(RUTA_LICENCIA, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        vence = data.get("vence", "")
        return datetime.fromisoformat(vence.replace("Z", "+00:00")) > datetime.now(timezone.utc)
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return False


def verificar_acceso():
    """
    Chequea si la app puede usarse: con licencia paga vigente, o dentro
    del trial gratuito. Efecto lateral: crea la marca de trial la primera
    vez que se llama (si todavía no existe).

    Devuelve: {"permitido": bool, "dias_restantes": int | None, "con_licencia": bool}
    dias_restantes es None cuando hay licencia paga (no aplica trial).
    """
    if _licencia_vigente():
        return {"permitido": True, "dias_restantes": None, "con_licencia": True}

    inicio_iso = _leer_marca_trial()
    if inicio_iso is None:
        inicio_iso = _crear_marca_trial()

    try:
        inicio = datetime.fromisoformat(inicio_iso)
    except ValueError:
        inicio = datetime.now(timezone.utc)

    ahora = datetime.now(timezone.utc)
    if ahora < inicio:
        # el reloj del sistema se movió para atrás respecto al primer
        # arranque: en vez de "regalar" días de trial, se corta.
        return {"permitido": False, "dias_restantes": 0, "con_licencia": False}

    transcurridos = (ahora - inicio).days
    restantes = max(0, TRIAL_DIAS - transcurridos)
    return {"permitido": restantes > 0, "dias_restantes": restantes, "con_licencia": False}
