// MV SQL NLP — capa multi-proveedor de IA (proceso principal, fetch nativo)
// El cliente elige: Anthropic, OpenAI, Gemini, Groq, Mistral, DeepSeek, xAI,
// Ollama local o cualquier endpoint OpenAI-compatible.

const PROVIDERS = {
  anthropic: { nombre: "Anthropic (Claude)", defaultModel: "claude-haiku-4-5-20251001",
    modelos: ["claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-opus-4-8"], needsKey: true },
  openai: { nombre: "OpenAI (GPT)", defaultModel: "gpt-4o-mini",
    modelos: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"], needsKey: true,
    base: "https://api.openai.com/v1" },
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

async function complete(ai, system, user, maxTokens = 1500) {
  const { provider, apiKey, model, baseUrl } = ai;
  const p = provider || "anthropic";

  if (p === "anthropic") {
    const data = await post("https://api.anthropic.com/v1/messages",
      { "x-api-key": apiKey, "anthropic-version": "2023-06-01" },
      { model: model || PROVIDERS.anthropic.defaultModel, max_tokens: maxTokens,
        temperature: 0, system, messages: [{ role: "user", content: user }] });
    return (data.content || []).map((b) => b.text || "").join("");
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
  const data = await post(`${base.replace(/\/$/, "")}/chat/completions`,
    { Authorization: `Bearer ${apiKey}` },
    { model: model || PROVIDERS[p]?.defaultModel || "gpt-4o-mini",
      max_tokens: maxTokens, temperature: 0,
      messages: [{ role: "system", content: system }, { role: "user", content: user }] });
  return data.choices?.[0]?.message?.content ?? "";
}

module.exports = { PROVIDERS, complete };
