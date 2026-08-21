# © 2026 Martín Viera. Todos los derechos reservados.

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


# ── Funciones que sí distinguen por plan ────────────────────────────
#
# verificar_acceso() de arriba es todo o nada: adentro o el cartel de
# comprar licencia. Pero la landing (web/index.html, planes Personal vs
# Profesional) promete una diferencia concreta entre esos dos planes:
# "Stored procedures + optimizador CTE" arranca en Profesional, no en
# Personal. Antes de esto no existía ningún código que la hiciera
# cumplir — un cliente de Personal (US$15) tenía exactamente las mismas
# funciones que uno de Profesional (US$29), pagara lo que pagara.
#
# El trial SÍ da estas funciones (la landing promete "todo incluido" los
# 7 días) y el propietario también (plan "propietario", nunca está en el
# set de abajo). Solo el plan Personal se queda afuera.
PLANES_SIN_FUNCIONES_AVANZADAS = {"personal"}


def _plan_licencia_vigente():
    """El campo `plan` de la licencia paga vigente, o None si no hay
    licencia paga vigente (trial, sin licencia, vencida o corrupta)."""
    if not os.path.exists(RUTA_LICENCIA):
        return None
    try:
        with open(RUTA_LICENCIA, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        vence = data.get("vence", "")
        if datetime.fromisoformat(vence.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            return None
        return data.get("plan")
    except (json.JSONDecodeError, KeyError, ValueError, OSError, TypeError):
        return None


def funciones_avanzadas_habilitadas():
    """Stored procedures y optimizador de CTE.

    True durante el trial (sin licencia paga: se asume que
    verificar_acceso() ya cortó el paso si el trial venció) y con
    cualquier licencia paga cuyo plan no sea "personal". Con Personal
    vigente, False — es la única función del producto que hoy discrimina
    por plan y no por rol de equipo (eso lo sigue resolviendo
    equipo.permisos() aparte, sin relación con esto).
    """
    plan = _plan_licencia_vigente()
    return plan is None or plan not in PLANES_SIN_FUNCIONES_AVANZADAS


# ── Renovación automática de la suscripción ────────────────────────
#
# Espejo de desktop/electron/services/licencia.cjs: los dos productos
# comparten UNA sola licencia, así que también tienen que compartir la
# forma de renovarla. Si solo Electron renovara, el mismo cliente con
# las dos versiones vería que una sigue andando y la otra le pide que
# compre de nuevo.
#
# Una suscripción cobra todos los meses; la licencia se emite una sola
# vez. Mientras dure un año eso solo le regala producto al que cancela,
# pero en cuanto la vigencia se acorte al ciclo de cobro —que es a
# donde tiene que ir— el cliente que SÍ paga se quedaría afuera todos
# los meses si nadie pide la licencia nueva por él.
#
# Regla de oro: nunca dejar al cliente peor que antes. Sin red, con el
# servidor caído o con una respuesta rota, se conserva la licencia que
# ya tenía y la app abre igual. Lo único que puede pasar es que mejore.

DIAS_ANTES_DE_RENOVAR = 5  # mismo margen que el producto Electron
_URL_RENOVAR = "https://mvsqlnlp.com/api/renovar-licencia"
_ESPERA_SEG = 8  # esto corre en el arranque: un servidor colgado no puede colgar la app


def _escribir_licencia(datos):
    """Escritura atómica: temporal + rename.

    Si se corta la luz a mitad de la escritura, el cliente conserva la
    licencia vieja en vez de quedarse con un JSON truncado que no
    parsea — o sea, sin licencia, justo cuando acaba de pagar.
    """
    tmp = RUTA_LICENCIA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, RUTA_LICENCIA)


def _vence_en(data):
    """Momento de vencimiento de una licencia, o None si no se puede leer."""
    try:
        return datetime.fromisoformat(str(data.get("vence", "")).replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def renovar_si_corresponde(abrir=None, ahora=None):
    """
    Pide una licencia nueva si la actual está por vencer y la
    suscripción sigue paga. No lanza nunca: devuelve por qué no se hizo.

    `abrir` se inyecta en los tests para no salir a la red de verdad.

    Estados: "sin-licencia" | "sin-token" | "al-dia" | "renovada" |
             "sin-red" | "rechazada" | "respuesta-invalida"
    """
    ahora = ahora or datetime.now(timezone.utc)

    if not os.path.exists(RUTA_LICENCIA):
        return {"estado": "sin-licencia"}
    try:
        with open(RUTA_LICENCIA, "r", encoding="utf-8") as fh:
            lic = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"estado": "sin-licencia"}

    # Las licencias viejas no llevan token. Sin él no hay con qué
    # acreditarse, y está bien que así sea: renovar por email dejaría
    # que cualquiera que lo conozca se lleve la licencia ajena.
    token = lic.get("token")
    if not token:
        return {"estado": "sin-token"}

    vence = _vence_en(lic)
    # Sin fecha legible se intenta igual: una licencia que la app no
    # sabe hasta cuándo vale es justamente una que conviene renovar.
    if vence is not None and (vence - ahora).days > DIAS_ANTES_DE_RENOVAR:
        return {"estado": "al-dia"}

    if abrir is None:
        from urllib.request import urlopen
        abrir = urlopen

    from urllib.parse import quote
    url = f"{_URL_RENOVAR}?token={quote(str(token), safe='')}"
    from urllib.error import HTTPError

    try:
        with abrir(url, timeout=_ESPERA_SEG) as r:
            codigo = getattr(r, "status", 200)
            cuerpo = json.loads(r.read().decode("utf-8"))
    except json.JSONDecodeError:
        return {"estado": "respuesta-invalida"}
    except HTTPError as e:
        # 402 (cancelada), 409 (pago único), 404, 500... urllib los tira
        # como excepción en vez de devolverlos. Se deja lo que hay: si
        # de verdad canceló, la licencia vence sola y ahí la puerta lo
        # frena. Borrarla acá convertiría un 500 nuestro en un cliente
        # bloqueado.
        return {"estado": "rechazada", "codigo": e.code}
    except Exception:
        # Sin red, DNS caído, timeout. La licencia actual queda intacta.
        return {"estado": "sin-red"}

    if codigo != 200:
        return {"estado": "rechazada", "codigo": codigo}

    nueva = (cuerpo or {}).get("licencia")
    # No se pisa nada hasta comprobar que lo nuevo sirve. Escribir una
    # licencia sin `vence` la dejaría muerta al instante, y el cliente
    # vería "comprá tu licencia" JUSTO después de renovar bien.
    if not isinstance(nueva, dict) or not nueva.get("token"):
        return {"estado": "respuesta-invalida"}
    nuevo_vence = _vence_en(nueva)
    if nuevo_vence is None or nuevo_vence <= ahora:
        return {"estado": "respuesta-invalida"}

    try:
        _escribir_licencia(nueva)
    except OSError:
        return {"estado": "respuesta-invalida"}
    return {"estado": "renovada", "vence": nueva.get("vence")}


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
