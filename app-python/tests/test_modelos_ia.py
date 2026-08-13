# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_modelos_ia.py — el cliente puede ver los modelos DE VERDAD de su cuenta
==================================================================
PROVEEDORES[...]["modelos"] es una lista fija en el código. Cada vez que
Anthropic, OpenAI, Groq o cualquier otro proveedor saca un modelo nuevo,
esa lista queda vieja hasta que alguien la actualice a mano y publique
una versión nueva del producto — mientras tanto el cliente no puede
elegir un modelo que ya está disponible y que su propia API key ya
puede usar.

listar_modelos() (proveedores_ia.py) resuelve eso consultando el
catálogo real del proveedor, con la API key que el cliente puso. Esto
prueba, por proveedor, que:

  - se arma la URL/headers correctos para pedir el listado;
  - el filtro saca los modelos que no sirven para esto (embeddings,
    audio, moderación) sin sacar los que sí sirven;
  - el orden prioriza el modelo más nuevo cuando el proveedor informa
    la fecha;
  - lo que NO tiene API de listado (Azure, MV SQL Créditos) falla con
    un mensaje que explica qué hacer, no con una excepción cruda;
  - sin API key no sale ni un pedido a la red.

Nota técnica: proveedores_ia.py importa `requests` a nivel de módulo.
Para que esto corra en una máquina sin `pip install -r requirements.txt`
(la promesa de este repo: los tests corren con la biblioteca estándar
sola), se stubea el módulo antes de importar — igual que test_privacidad.py
hace con motor.py.
"""
import json
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))


class _ErrorConexionFalso(Exception):
    pass


class _ErrorTimeoutFalso(Exception):
    pass


_requests_falso = types.ModuleType("requests")
_requests_falso.exceptions = types.SimpleNamespace(
    ConnectionError=_ErrorConexionFalso, Timeout=_ErrorTimeoutFalso)
sys.modules.setdefault("requests", _requests_falso)

import proveedores_ia  # noqa: E402

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


class _RespuestaFalsa:
    def __init__(self, status_code, cuerpo):
        self.status_code = status_code
        self._cuerpo = cuerpo
        self.text = json.dumps(cuerpo)

    def json(self):
        return self._cuerpo


def _get_falso(status_code=200, cuerpo=None):
    """Reemplaza requests.get y anota cada pedido (url, headers, params)."""
    llamadas = []

    def get(url, headers=None, params=None, timeout=None):
        llamadas.append({"url": url, "headers": headers or {}, "params": params or {}})
        return _RespuestaFalsa(status_code, cuerpo if cuerpo is not None else {})
    get.llamadas = llamadas
    return get


print("\n== El cliente ve los modelos reales de su cuenta ==")


@test("ANTHROPIC: pide con x-api-key y devuelve los ids, más nuevo primero")
def _():
    get = _get_falso(cuerpo={"data": [
        {"id": "claude-haiku-4-5-20251001", "created_at": "2025-10-01T00:00:00Z"},
        {"id": "claude-opus-4-8", "created_at": "2026-01-15T00:00:00Z"},
    ]})
    proveedores_ia.requests.get = get
    modelos = proveedores_ia.listar_modelos("anthropic", api_key="sk-ant-x")
    assert modelos == ["claude-opus-4-8", "claude-haiku-4-5-20251001"], modelos
    assert get.llamadas[0]["headers"]["x-api-key"] == "sk-ant-x", \
        "no mandó la API key en el header que Anthropic espera"
    assert "anthropic.com" in get.llamadas[0]["url"]


@test("OPENAI: filtra embeddings/whisper/tts y ordena por fecha de creación")
def _():
    get = _get_falso(cuerpo={"data": [
        {"id": "text-embedding-3-small", "created": 100},
        {"id": "gpt-4o-mini", "created": 200},
        {"id": "whisper-1", "created": 300},
        {"id": "gpt-4.1", "created": 400},
    ]})
    proveedores_ia.requests.get = get
    modelos = proveedores_ia.listar_modelos("openai", api_key="sk-x")
    assert modelos == ["gpt-4.1", "gpt-4o-mini"], \
        f"no filtró/ordenó bien: {modelos}"
    assert get.llamadas[0]["headers"]["Authorization"] == "Bearer sk-x"
    assert get.llamadas[0]["url"] == "https://api.openai.com/v1/models"


@test("GROQ y los demás OpenAI-compatibles usan su propia base URL")
def _():
    get = _get_falso(cuerpo={"data": [{"id": "llama-3.3-70b-versatile", "created": 1}]})
    proveedores_ia.requests.get = get
    proveedores_ia.listar_modelos("groq", api_key="gsk-x")
    assert get.llamadas[0]["url"] == "https://api.groq.com/openai/v1/models", \
        f"le pidió a la URL equivocada: {get.llamadas[0]['url']}"


@test("GEMINI: solo los modelos que soportan generateContent, sin el prefijo 'models/'")
def _():
    get = _get_falso(cuerpo={"models": [
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent", "countTokens"]},
    ]})
    proveedores_ia.requests.get = get
    modelos = proveedores_ia.listar_modelos("gemini", api_key="AIza-x")
    assert modelos == ["gemini-2.5-pro", "gemini-2.0-flash"], modelos
    assert get.llamadas[0]["params"]["key"] == "AIza-x"


@test("OLLAMA: no pide API key y usa localhost por defecto")
def _():
    get = _get_falso(cuerpo={"models": [
        {"name": "llama3.1", "modified_at": "2026-01-01T00:00:00Z"},
        {"name": "qwen2.5-coder", "modified_at": "2026-03-01T00:00:00Z"},
    ]})
    proveedores_ia.requests.get = get
    modelos = proveedores_ia.listar_modelos("ollama")  # sin api_key
    assert modelos == ["qwen2.5-coder", "llama3.1"], modelos
    assert get.llamadas[0]["url"] == "http://localhost:11434/api/tags"


@test("OLLAMA remoto: respeta la Base URL que puso el cliente")
def _():
    get = _get_falso(cuerpo={"models": [{"name": "sqlcoder", "modified_at": "x"}]})
    proveedores_ia.requests.get = get
    proveedores_ia.listar_modelos("ollama", base_url="http://192.168.1.50:11434")
    assert get.llamadas[0]["url"] == "http://192.168.1.50:11434/api/tags"


@test("CUSTOM funciona con la Base URL propia, vía el camino OpenAI-compatible")
def _():
    get = _get_falso(cuerpo={"data": [{"id": "mi-modelo-propio", "created": 1}]})
    proveedores_ia.requests.get = get
    modelos = proveedores_ia.listar_modelos(
        "custom", api_key="x", base_url="https://miendpoint.com/v1")
    assert modelos == ["mi-modelo-propio"]
    assert get.llamadas[0]["url"] == "https://miendpoint.com/v1/models"


@test("CUSTOM sin Base URL no sale a ningún lado: no hay a quién preguntarle")
def _():
    get = _get_falso(cuerpo={"data": []})
    proveedores_ia.requests.get = get
    try:
        proveedores_ia.listar_modelos("custom", api_key="x")
        raise AssertionError("no lanzó ErrorProveedor")
    except proveedores_ia.ErrorProveedor:
        pass
    assert not get.llamadas, "salió a la red sin saber a quién preguntarle"


@test("AZURE no tiene listado por API: falla con una explicación, no una excepción cruda")
def _():
    get = _get_falso()
    proveedores_ia.requests.get = get
    try:
        proveedores_ia.listar_modelos("azure", api_key="x", base_url="https://r.openai.azure.com")
        raise AssertionError("no lanzó ErrorProveedor")
    except proveedores_ia.ErrorProveedor as e:
        assert "deployment" in str(e).lower(), f"no explica qué hacer: {e}"
    assert not get.llamadas, "azure no tiene API de listado: no debería haber salido a la red"


@test("MV SQL CRÉDITOS no tiene modelos para elegir: no es un error de conexión")
def _():
    try:
        proveedores_ia.listar_modelos("mvsql_creditos")
        raise AssertionError("no lanzó ErrorProveedor")
    except proveedores_ia.ErrorProveedor:
        pass


@test("SIN API KEY no sale ni un pedido a la red")
def _():
    get = _get_falso(cuerpo={"data": [{"id": "gpt-4o", "created": 1}]})
    proveedores_ia.requests.get = get
    try:
        proveedores_ia.listar_modelos("openai")  # sin api_key
        raise AssertionError("no lanzó ErrorProveedor")
    except proveedores_ia.ErrorProveedor:
        pass
    assert not get.llamadas, \
        "salió a pedir el listado sin tener con qué autenticarse: la respuesta iba a ser 401 igual"


@test("un proveedor que solo tiene modelos no-chat devuelve lista vacía, no un error")
def _():
    # Una lista vacía significa "no hay nada nuevo que elegir", que la UI
    # muestra como aviso, no como falla — no es lo mismo que no poder
    # conectar con el proveedor.
    get = _get_falso(cuerpo={"data": [{"id": "text-embedding-3-small", "created": 1}]})
    proveedores_ia.requests.get = get
    modelos = proveedores_ia.listar_modelos("openai", api_key="x")
    assert modelos == []


@test("un 401 del proveedor se traduce a un mensaje accionable")
def _():
    get = _get_falso(status_code=401, cuerpo={})
    proveedores_ia.requests.get = get
    try:
        proveedores_ia.listar_modelos("openai", api_key="key-vencida")
        raise AssertionError("no lanzó ErrorProveedor con un 401")
    except proveedores_ia.ErrorProveedor as e:
        assert "API key" in str(e), f"el mensaje no dice qué está mal: {e}"


@test("proveedor desconocido no revienta con un KeyError")
def _():
    try:
        proveedores_ia.listar_modelos("proveedor-que-no-existe", api_key="x")
        raise AssertionError("no lanzó ErrorProveedor")
    except proveedores_ia.ErrorProveedor:
        pass
    except KeyError:
        raise AssertionError("dejó escapar un KeyError crudo en vez de ErrorProveedor")


print(f"\n  {_pasadas} pasadas · {_falladas} falladas\n")
sys.exit(1 if _falladas else 0)
