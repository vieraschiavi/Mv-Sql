# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_renovacion.py — la app Python también renueva la licencia sola
==================================================================
Los dos productos comparten UNA sola licencia (la web emite una y sirve
para el .exe y para el .bat). Si solo Electron renovara, el mismo
cliente con las dos versiones vería que una sigue andando y la otra le
pide que compre de nuevo — con el mismo archivo, el mismo día.

Lo que se fija acá es sobre todo lo que NO tiene que pasar. Renovar no
puede dejar al cliente peor que antes: sin red, con el servidor caído,
con una respuesta rota o con la suscripción cancelada, la licencia que
ya tenía queda intacta y la app abre igual.

El caso caro y silencioso es el de la licencia nueva SIN `vence`: se
escribiría encima de la buena, _licencia_vigente() daría False al
instante, y el cliente vería "comprá tu licencia" justo después de una
renovación exitosa.
"""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import licencia  # noqa: E402

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


_URL = "https://mvsqlnlp.com/api/renovar-licencia"


def en_dias(n):
    return (datetime.now(timezone.utc) + timedelta(days=n)).isoformat()


class _Resp(io.BytesIO):
    """Lo mínimo que devuelve urlopen: un archivo con .status."""

    def __init__(self, status, cuerpo):
        super().__init__(json.dumps(cuerpo).encode("utf-8"))
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(codigo):
    """El 4xx/5xx tal como lo tira urllib: como excepción, no como respuesta."""
    return HTTPError(_URL, codigo, "error", {}, None)


def abridor(status=200, cuerpo=None, error=None):
    """urlopen falso que anota las URLs que le pidieron."""
    llamadas = []

    def abrir(url, timeout=None):
        llamadas.append(url)
        if error is not None:
            raise error
        return _Resp(status, cuerpo or {})

    abrir.llamadas = llamadas
    return abrir


# La licencia vive al lado del código (licencia.RUTA_LICENCIA), así que
# cada caso escribe la suya y al final se restaura lo que hubiera.
_PREVIO = (open(licencia.RUTA_LICENCIA, "rb").read()
           if os.path.exists(licencia.RUTA_LICENCIA) else None)


def poner_licencia(**extra):
    lic = {"producto": "MV SQL NLP", "email": "cliente@empresa.com",
           "plan": "profesional", "modo": "own_ai",
           "token": "el-token-del-cliente", "vence": en_dias(2)}
    lic.update(extra)
    lic = {k: v for k, v in lic.items() if v is not None}
    with open(licencia.RUTA_LICENCIA, "w", encoding="utf-8") as fh:
        json.dump(lic, fh)
    return lic


def sin_licencia():
    if os.path.exists(licencia.RUTA_LICENCIA):
        os.remove(licencia.RUTA_LICENCIA)


def guardada():
    with open(licencia.RUTA_LICENCIA, "r", encoding="utf-8") as fh:
        return json.load(fh)


print("\n== La app Python renueva la licencia sola ==")


@test("CON LA LICENCIA POR VENCER Y LA SUSCRIPCIÓN PAGA, la renueva")
def _():
    poner_licencia()
    nueva = {"producto": "MV SQL NLP", "modo": "own_ai", "token": "token-nuevo",
             "plan": "profesional", "email": "cliente@empresa.com", "vence": en_dias(35)}
    r = licencia.renovar_si_corresponde(
        abrir=abridor(200, {"token": "token-nuevo", "licencia": nueva}))
    assert r["estado"] == "renovada", f"no renovó: {r}"
    assert guardada()["token"] == "token-nuevo", \
        "dijo que renovó pero el archivo quedó con la licencia vieja"


@test("manda el token escapado, que es con lo que se acredita")
def _():
    # Renovar por email dejaría que cualquiera que lo conozca se lleve
    # la licencia ajena.
    poner_licencia(token="tok en&raro")
    a = abridor(402, {})
    licencia.renovar_si_corresponde(abrir=a)
    assert len(a.llamadas) == 1
    assert "token=tok%20en%26raro" in a.llamadas[0], a.llamadas[0]


@test("con la licencia lejos de vencer NO sale a la red")
def _():
    # Salir en cada arranque sería un pedido por cliente por día, todo
    # el año, para no hacer nada.
    poner_licencia(vence=en_dias(200))
    a = abridor(200, {})
    r = licencia.renovar_si_corresponde(abrir=a)
    assert r["estado"] == "al-dia", r
    assert not a.llamadas, "consultó al servidor sin necesidad"


@test("SIN RED la licencia queda intacta y la app abre igual")
def _():
    # El cliente en una empresa con el firewall cerrado.
    poner_licencia()
    r = licencia.renovar_si_corresponde(abrir=abridor(error=URLError("ENOTFOUND")))
    assert r["estado"] == "sin-red", r
    assert guardada()["token"] == "el-token-del-cliente", \
        "se quedó sin licencia por no tener internet"


@test("SI EL SERVIDOR FALLA (500) no le borra la licencia al cliente")
def _():
    # Un error nuestro no puede convertirse en un cliente bloqueado.
    # urllib tira los 4xx/5xx como excepción en vez de devolverlos, que
    # es justo la forma en que este caso se escapa si no se prueba.
    poner_licencia()
    r = licencia.renovar_si_corresponde(abrir=abridor(error=http_error(500)))
    assert r["estado"] == "rechazada", r
    assert r.get("codigo") == 500, r
    assert os.path.exists(licencia.RUTA_LICENCIA), "borró la licencia por un 500 del servidor"
    assert guardada()["token"] == "el-token-del-cliente"


@test("con la suscripción cancelada (402) tampoco la borra: la deja vencer")
def _():
    # Quien canceló pierde el acceso cuando la licencia vence, no antes:
    # pudo haber pagado hasta fin de mes.
    poner_licencia()
    r = licencia.renovar_si_corresponde(abrir=abridor(error=http_error(402)))
    assert r["estado"] == "rechazada", r
    assert r.get("codigo") == 402, r
    assert guardada()["token"] == "el-token-del-cliente"


@test("un pago único (409) no rompe nada: se deja la licencia como está")
def _():
    poner_licencia()
    r = licencia.renovar_si_corresponde(abrir=abridor(error=http_error(409)))
    assert r["estado"] == "rechazada", r
    assert guardada()["token"] == "el-token-del-cliente"


@test("UNA RESPUESTA SIN `vence` NO SE GUARDA")
def _():
    # El bug caro y silencioso: pisaría la licencia buena con una que
    # nace muerta, y el cliente vería "comprá tu licencia" justo después
    # de renovar bien.
    poner_licencia()
    r = licencia.renovar_si_corresponde(
        abrir=abridor(200, {"licencia": {"token": "x", "plan": "profesional"}}))
    assert r["estado"] == "respuesta-invalida", r
    assert guardada()["token"] == "el-token-del-cliente", \
        "pisó la licencia buena con una que nace vencida"


@test("una licencia nueva ya vencida tampoco se guarda")
def _():
    poner_licencia()
    r = licencia.renovar_si_corresponde(
        abrir=abridor(200, {"licencia": {"token": "x", "vence": en_dias(-1)}}))
    assert r["estado"] == "respuesta-invalida", r
    assert guardada()["token"] == "el-token-del-cliente"


@test("una licencia sin token (comprada antes) no intenta renovar")
def _():
    poner_licencia(token=None)
    a = abridor(200, {})
    r = licencia.renovar_si_corresponde(abrir=a)
    assert r["estado"] == "sin-token", r
    assert not a.llamadas


@test("un cliente en prueba (sin licencia) no consulta nada")
def _():
    sin_licencia()
    a = abridor(200, {})
    r = licencia.renovar_si_corresponde(abrir=a)
    assert r["estado"] == "sin-licencia", r
    assert not a.llamadas, "consultó por alguien que nunca compró"


@test("la licencia renovada la da por vigente el mismo chequeo que usa la app")
def _():
    # El viaje corto pero completo: renovar y que verificar_acceso() lo
    # note. Sin esto, "renovada" podría ser cierto y la app bloquear igual.
    poner_licencia(vence=en_dias(-1))          # vencida: sin renovar, la app corta
    nueva = {"producto": "MV SQL NLP", "modo": "own_ai", "token": "token-nuevo",
             "plan": "profesional", "email": "c@e.com", "vence": en_dias(35)}
    r = licencia.renovar_si_corresponde(abrir=abridor(200, {"licencia": nueva}))
    assert r["estado"] == "renovada", r
    acceso = licencia.verificar_acceso()
    assert acceso["permitido"] and acceso["con_licencia"], \
        f"renovó y la app igual lo trata como prueba gratuita: {acceso}"


@test("app.py la llama, y cacheada (si no, sale a la red en cada clic)")
def _():
    # Este bloque de app.py corre en CADA rerun de Streamlit. Sin caché
    # sería un pedido HTTP por clic del usuario.
    src = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    assert "renovar_si_corresponde" in src, \
        "app.py nunca renueva: el endpoint queda sin cliente del lado Python"
    i = src.index("def _renovar_una_vez")
    assert "cache_resource" in src[max(0, i - 200):i], \
        "la renovación no está cacheada: sale a la red en cada rerun"
    assert src.index("_renovar_una_vez()") < src.index("_acceso = verificar_acceso()"), \
        "renueva después de chequear el acceso, o sea tarde"


# Se restaura lo que hubiera antes de correr los tests.
if _PREVIO is None:
    if os.path.exists(licencia.RUTA_LICENCIA):
        os.remove(licencia.RUTA_LICENCIA)
else:
    open(licencia.RUTA_LICENCIA, "wb").write(_PREVIO)

print(f"\n  {_pasadas} pasadas · {_falladas} falladas\n")
sys.exit(1 if _falladas else 0)
