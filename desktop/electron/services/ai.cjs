/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — capa multi-proveedor de IA (proceso principal, fetch nativo)
// El cliente elige: Anthropic, OpenAI, Gemini, Groq, Mistral, DeepSeek, xAI,
// Ollama local o cualquier endpoint OpenAI-compatible.

const PROVIDERS = {
  anthropic: { nombre: "Anthropic (Claude)", defaultModel: "claude-haiku-4-5-20251001",
    modelos: ["claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-opus-4-8"], needsKey: true },
  openai: { nombre: "OpenAI (GPT)", defaultModel: "gpt-4o-mini",
    modelos: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"], needsKey: true,
    base: "https://api.openai.com/v1" },
  azure: { nombre: "Microsoft Copilot (Azure OpenAI)", defaultModel: "", modelos: [],
    needsKey: true },
  gemini: { nombre: "Google (Gemini)", defaultModel: "gemini-2.0-flash",
    modelos: ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"], needsKey: true },
  groq: { nombre: "Groq (Llama)", defaultModel: "llama-3.3-70b-versatile",
    modelos: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"], needsKey: true,
    base: "https://api.groq.com/openai/v1" },
  mistral: { nombre: "Mistral AI", defaultModel: "mistral-small-latest",
    modelos: ["mistral-small-latest", "mistral-large-latest", "codestral-latest"], needsKey: true,
    base: "https://api.mistral.ai/v1" },
  deepseek: { nombre: "DeepSeek", defaultModel: "deepseek-chat",
    modelos: ["deepseek-chat", "deepseek-reasoner"], needsKey: true,
    base: "https://api.deepseek.com/v1" },
  xai: { nombre: "xAI (Grok)", defaultModel: "grok-3-mini",
    modelos: ["grok-3-mini", "grok-3"], needsKey: true, base: "https://api.x.ai/v1" },
  ollama: { nombre: "Ollama (local, gratis)", defaultModel: "llama3.1",
    modelos: ["llama3.1", "qwen2.5-coder", "mistral", "sqlcoder"], needsKey: false },
  custom: { nombre: "Otro (OpenAI-compatible)", defaultModel: "", modelos: [], needsKey: true },
};

async function get(url, headers) {
  let r;
  try {
    r = await fetch(url, { headers, signal: AbortSignal.timeout(20000) });
  } catch (e) {
    throw new Error(`No se pudo conectar al proveedor de IA: ${e.message}`);
  }
  if (r.status === 401) throw new Error("API key inválida o vencida (401). Revisá la clave en Configuración.");
  if (r.status === 429) throw new Error("Límite del proveedor alcanzado (429). Probá de nuevo en unos segundos.");
  if (!r.ok) throw new Error(`Error del proveedor (${r.status}): ${(await r.text()).slice(0, 300)}`);
  return r.json();
}

async function post(url, headers, body) {
  let r;
  try {
    r = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", ...headers },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(90000),
    });
  } catch (e) {
    throw new Error(`No se pudo conectar al proveedor de IA: ${e.message}`);
  }
  if (r.status === 401) throw new Error("API key inválida o vencida (401). Revisá la clave en Configuración.");
  if (r.status === 429) throw new Error("Límite del proveedor alcanzado (429). Probá de nuevo en unos segundos.");
  if (!r.ok) throw new Error(`Error del proveedor (${r.status}): ${(await r.text()).slice(0, 300)}`);
  return r.json();
}

// Modelos nuevos rechazan `temperature` (Claude Opus 4.8+) o piden
// `max_completion_tokens` (OpenAI GPT-5+): adaptar el payload y reintentar.
async function postConReintento(url, headers, payload) {
  try {
    return await post(url, headers, payload);
  } catch (e) {
    const msg = String(e.message || e);
    let cambiado = false;
    if (msg.includes("temperature") && "temperature" in payload) {
      delete payload.temperature;
      cambiado = true;
    }
    if (msg.includes("max_completion_tokens") && "max_tokens" in payload) {
      payload.max_completion_tokens = payload.max_tokens;
      delete payload.max_tokens;
      cambiado = true;
    }
    if (!cambiado) throw e;
    return post(url, headers, payload);
  }
}

async function complete(ai, system, user, maxTokens = 1500) {
  const { provider, apiKey, model, baseUrl } = ai;
  const p = provider || "anthropic";

  if (p === "anthropic") {
    const data = await postConReintento("https://api.anthropic.com/v1/messages",
      { "x-api-key": apiKey, "anthropic-version": "2023-06-01" },
      { model: model || PROVIDERS.anthropic.defaultModel, max_tokens: maxTokens,
        temperature: 0, system, messages: [{ role: "user", content: user }] });
    return (data.content || []).map((b) => b.text || "").join("");
  }

  if (p === "azure") {
    // Azure OpenAI (el backend de Microsoft Copilot para empresas).
    // baseUrl: https://<recurso>.openai.azure.com — model = nombre del deployment.
    if (!baseUrl) throw new Error(
      "Azure OpenAI necesita la URL del recurso (ej: https://mirecurso.openai.azure.com) " +
      "en Base URL, y el nombre del deployment en Modelo.");
    const data = await postConReintento(
      `${baseUrl.replace(/\/$/, "")}/openai/deployments/${model || "gpt-4o-mini"}/chat/completions?api-version=2024-06-01`,
      { "api-key": apiKey },
      { max_tokens: maxTokens, temperature: 0,
        messages: [{ role: "system", content: system }, { role: "user", content: user }] });
    return data.choices?.[0]?.message?.content ?? "";
  }

  if (p === "gemini") {
    const m = model || PROVIDERS.gemini.defaultModel;
    const data = await post(
      `https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${apiKey}`,
      {},
      { system_instruction: { parts: [{ text: system }] },
        contents: [{ role: "user", parts: [{ text: user }] }],
        generationConfig: { maxOutputTokens: maxTokens, temperature: 0 } });
    return data.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
  }

  if (p === "ollama") {
    const base = (baseUrl || "http://localhost:11434").replace(/\/$/, "");
    const data = await post(`${base}/api/chat`, {},
      { model: model || PROVIDERS.ollama.defaultModel, stream: false,
        options: { temperature: 0 },
        messages: [{ role: "system", content: system }, { role: "user", content: user }] });
    return data.message?.content ?? "";
  }

  const base = baseUrl || PROVIDERS[p]?.base;
  if (!base) throw new Error(`El proveedor '${p}' necesita una Base URL (endpoint OpenAI-compatible).`);
  const data = await postConReintento(`${base.replace(/\/$/, "")}/chat/completions`,
    { Authorization: `Bearer ${apiKey}` },
    { model: model || PROVIDERS[p]?.defaultModel || "gpt-4o-mini",
      max_tokens: maxTokens, temperature: 0,
      messages: [{ role: "system", content: system }, { role: "user", content: user }] });
  return data.choices?.[0]?.message?.content ?? "";
}

// ── Listado de modelos EN VIVO ─────────────────────────────────────
//
// PROVIDERS[...].modelos es una lista fija que se desactualiza en cuanto
// el proveedor saca un modelo nuevo — y eso pasa seguido: haría falta
// tocar código y republicar un .exe para que el cliente pueda elegir un
// modelo que salió la semana pasada. Estas funciones consultan el
// catálogo real por API, con la API key que el cliente ya puso, para
// que la lista esté al día sin depender de un release nuestro.
//
// Espejo de _modelos_* / listar_modelos() en app-python/proveedores_ia.py:
// mismos endpoints, mismos filtros, mismo criterio de orden. Los dos
// productos comparten el mismo catálogo de proveedores; que uno ofrezca
// un modelo nuevo y el otro no sería confundir al mismo cliente según
// qué versión abrió.

// Ids que aparecen en el listado pero no sirven para chat (embeddings,
// audio, moderación, imagen). No es exhaustivo a propósito: ante la
// duda se incluye, porque un modelo de más se descarta con la vista y
// uno de menos ni se sabe que faltó.
const NO_CHAT = ["embed", "whisper", "tts", "dall-e", "moderation", "clip",
  "davinci-002", "babbage-002", "text-moderation"];
const esModeloChat = (id) => {
  const bajo = id.toLowerCase();
  return !NO_CHAT.some((x) => bajo.includes(x));
};

async function modelosAnthropic(apiKey) {
  const data = await get("https://api.anthropic.com/v1/models?limit=100",
    { "x-api-key": apiKey, "anthropic-version": "2023-06-01" });
  const items = (data.data || []).filter((m) => m.id);
  items.sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
  return items.map((m) => m.id);
}

async function modelosOpenAiCompat(base, apiKey) {
  const data = await get(`${base.replace(/\/$/, "")}/models`, { Authorization: `Bearer ${apiKey}` });
  const items = (data.data || []).filter((m) => m.id && esModeloChat(m.id));
  items.sort((a, b) => (b.created || 0) - (a.created || 0));
  return items.map((m) => m.id);
}

async function modelosGemini(apiKey) {
  const data = await get(
    `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}&pageSize=1000`, {});
  return (data.models || [])
    .filter((m) => (m.supportedGenerationMethods || []).includes("generateContent"))
    .map((m) => String(m.name || "").split("/").pop())
    .filter(Boolean);
}

async function modelosOllama(baseUrl) {
  const base = (baseUrl || "http://localhost:11434").replace(/\/$/, "");
  const data = await get(`${base}/api/tags`, {});
  const items = (data.models || []).filter((m) => m.name || m.model);
  items.sort((a, b) => String(b.modified_at || "").localeCompare(String(a.modified_at || "")));
  return items.map((m) => m.name || m.model);
}

/**
 * Trae del proveedor la lista real de modelos para esa API key, más
 * nuevos primero cuando el proveedor informa la fecha.
 *
 * No tira para "no hay modelos nuevos" (eso es una lista vacía, no un
 * error) — SÍ tira para lo que impide seguir: proveedor sin listado por
 * API, sin key, o cualquier falla de red que ya maneja get().
 */
async function listModels(provider, apiKey, baseUrl) {
  const p = (provider || "").toLowerCase();
  const info = PROVIDERS[p];
  if (!info) throw new Error(`Proveedor desconocido: ${p}`);

  if (p === "azure") {
    // El listado real de deployments de Azure OpenAI se hace con
    // credenciales de gestión de Azure (Azure AD), no con la api-key
    // del recurso — no hay una API simple y equivalente acá. El nombre
    // del deployment se sigue escribiendo a mano.
    throw new Error("Azure OpenAI no expone sus modelos por esta vía: escribí el nombre del deployment a mano.");
  }
  if (info.needsKey && !apiKey) throw new Error("Falta la API key.");

  if (p === "anthropic") return modelosAnthropic(apiKey);
  if (p === "gemini") return modelosGemini(apiKey);
  if (p === "ollama") return modelosOllama(baseUrl);

  const base = baseUrl || info.base;
  if (!base) throw new Error(`El proveedor '${p}' necesita una Base URL para listar modelos.`);
  return modelosOpenAiCompat(base, apiKey);
}

module.exports = { PROVIDERS, complete, listModels };
