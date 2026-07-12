"""
proveedores_ia.py — MV SQL NLP
==================================================================
Capa unificada de proveedores de IA. El cliente elige QUÉ IA usa:
Anthropic (Claude), OpenAI (GPT), Google (Gemini), Groq, Mistral,
DeepSeek, xAI (Grok), Ollama (local, gratis) o cualquier endpoint
compatible con la API de OpenAI.

Todo por REST puro (requests) — sin SDKs, sin dependencias pesadas.
==================================================================
"""

import json
import os
import requests

TIMEOUT = 90

RUTA_LICENCIA = os.path.join(os.path.dirname(__file__), "licencia_mvsql.json")


def cargar_licencia_creditos():
    """Si el zip descargado incluye créditos embebidos, devuelve la licencia."""
    if not os.path.exists(RUTA_LICENCIA):
        return None
    try:
        with open(RUTA_LICENCIA, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# Catálogo de proveedores soportados "de fábrica".
# El usuario puede además agregar un proveedor "custom" (OpenAI-compatible).
PROVEEDORES = {
    "mvsql_creditos": {
        "nombre": "MV SQL Créditos (sin API key)",
        "modelos": [],
        "modelo_default": "",
        "necesita_key": False,
        "url_keys": "https://mvsqlnlp.com/#pricing",
    },
    "anthropic": {
        "nombre": "Anthropic (Claude)",
        "modelos": ["claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-opus-4-8"],
        "modelo_default": "claude-haiku-4-5-20251001",
        "necesita_key": True,
        "url_keys": "https://console.anthropic.com/",
    },
    "openai": {
        "nombre": "OpenAI (GPT)",
        "modelos": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
        "modelo_default": "gpt-4o-mini",
        "necesita_key": True,
        "url_keys": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "nombre": "Google (Gemini)",
        "modelos": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"],
        "modelo_default": "gemini-2.0-flash",
        "necesita_key": True,
        "url_keys": "https://aistudio.google.com/apikey",
    },
    "groq": {
        "nombre": "Groq (Llama, ultra rápido)",
        "modelos": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "modelo_default": "llama-3.3-70b-versatile",
        "necesita_key": True,
        "url_keys": "https://console.groq.com/keys",
    },
    "mistral": {
        "nombre": "Mistral AI",
        "modelos": ["mistral-small-latest", "mistral-large-latest", "codestral-latest"],
        "modelo_default": "mistral-small-latest",
        "necesita_key": True,
        "url_keys": "https://console.mistral.ai/",
    },
    "deepseek": {
        "nombre": "DeepSeek",
        "modelos": ["deepseek-chat", "deepseek-reasoner"],
        "modelo_default": "deepseek-chat",
        "necesita_key": True,
        "url_keys": "https://platform.deepseek.com/",
    },
    "xai": {
        "nombre": "xAI (Grok)",
        "modelos": ["grok-3-mini", "grok-3"],
        "modelo_default": "grok-3-mini",
        "necesita_key": True,
        "url_keys": "https://console.x.ai/",
    },
    "ollama": {
        "nombre": "Ollama (local, sin costo)",
        "modelos": ["llama3.1", "qwen2.5-coder", "mistral", "sqlcoder"],
        "modelo_default": "llama3.1",
        "necesita_key": False,
        "url_keys": "https://ollama.com/download",
    },
    "custom": {
        "nombre": "Otro (endpoint OpenAI-compatible)",
        "modelos": [],
        "modelo_default": "",
        "necesita_key": True,
        "url_keys": "",
    },
}

# Endpoints OpenAI-compatibles (chat/completions)
_BASES_OPENAI_COMPAT = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "xai": "https://api.x.ai/v1",
}


class ErrorProveedor(RuntimeError):
    pass


def _post(url, headers, payload):
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.exceptions.ConnectionError as e:
        raise ErrorProveedor(f"No se pudo conectar al proveedor ({url}): {e}")
    except requests.exceptions.Timeout:
        raise ErrorProveedor("El proveedor de IA tardó demasiado en responder (timeout).")
    if r.status_code == 401:
        raise ErrorProveedor("API key inválida o vencida (401). Verificá la clave en Configuración.")
    if r.status_code == 429:
        raise ErrorProveedor("Límite de uso del proveedor alcanzado (429). Esperá unos segundos o cambiá de proveedor.")
    if r.status_code >= 400:
        raise ErrorProveedor(f"Error del proveedor ({r.status_code}): {r.text[:300]}")
    return r.json()


def completar(proveedor, api_key, system, user, modelo=None, max_tokens=1500,
              base_url=None, temperatura=0.0):
    """
    Punto único de entrada: manda (system, user) al proveedor elegido
    y devuelve el texto de respuesta.

    proveedor: clave de PROVEEDORES ('anthropic', 'openai', 'gemini', ...)
    base_url:  para 'custom' (endpoint OpenAI-compatible) u 'ollama' remoto.
    """
    proveedor = (proveedor or "anthropic").lower()

    if proveedor == "mvsql_creditos":
        licencia = cargar_licencia_creditos()
        if not licencia:
            raise ErrorProveedor(
                "No se encontró licencia_mvsql.json. Este proveedor solo funciona en el "
                "zip descargado con el plan de créditos embebidos — comprá uno en "
                "mvsqlnlp.com o elegí otro proveedor y pon tu propia API key.")
        data = _post(
            licencia["proxy_url"], {"content-type": "application/json"},
            {"token": licencia["token"], "system": system, "user": user,
             "max_tokens": max_tokens},
        )
        if "error" in data:
            raise ErrorProveedor(data["error"])
        return data.get("text", "")

    if proveedor == "anthropic":
        data = _post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": api_key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            {"model": modelo or PROVEEDORES["anthropic"]["modelo_default"],
             "max_tokens": max_tokens, "temperature": temperatura,
             "system": system,
             "messages": [{"role": "user", "content": user}]},
        )
        return "".join(b.get("text", "") for b in data.get("content", []))

    if proveedor == "gemini":
        m = modelo or PROVEEDORES["gemini"]["modelo_default"]
        data = _post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}",
            {"content-type": "application/json"},
            {"system_instruction": {"parts": [{"text": system}]},
             "contents": [{"role": "user", "parts": [{"text": user}]}],
             "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperatura}},
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ErrorProveedor(f"Respuesta inesperada de Gemini: {json.dumps(data)[:300]}")

    if proveedor == "ollama":
        base = (base_url or "http://localhost:11434").rstrip("/")
        data = _post(
            f"{base}/api/chat", {"content-type": "application/json"},
            {"model": modelo or PROVEEDORES["ollama"]["modelo_default"],
             "stream": False, "options": {"temperature": temperatura},
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}]},
        )
        return data.get("message", {}).get("content", "")

    # Resto: API OpenAI-compatible (openai, groq, mistral, deepseek, xai, custom)
    base = base_url or _BASES_OPENAI_COMPAT.get(proveedor)
    if not base:
        raise ErrorProveedor(f"Proveedor '{proveedor}' requiere base_url (endpoint OpenAI-compatible).")
    info = PROVEEDORES.get(proveedor, {})
    data = _post(
        f"{base.rstrip('/')}/chat/completions",
        {"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
        {"model": modelo or info.get("modelo_default") or "gpt-4o-mini",
         "max_tokens": max_tokens, "temperature": temperatura,
         "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": user}]},
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise ErrorProveedor(f"Respuesta inesperada del proveedor: {json.dumps(data)[:300]}")


def probar_conexion(proveedor, api_key, modelo=None, base_url=None):
    """Prueba rápida de credenciales. Devuelve (ok, mensaje)."""
    try:
        txt = completar(proveedor, api_key, "Respondé solo con la palabra OK.",
                        "ping", modelo=modelo, max_tokens=10, base_url=base_url)
        return True, f"Conexión OK — respuesta: {txt.strip()[:40]}"
    except Exception as e:
        return False, str(e)
