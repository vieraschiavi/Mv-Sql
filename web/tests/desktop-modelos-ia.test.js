/** El cliente ve los modelos DE VERDAD de su cuenta (desktop/electron/services/ai.cjs).
 *
 * Espejo de app-python/tests/test_modelos_ia.py: los dos productos
 * comparten el mismo catálogo de proveedores y tienen que ofrecer los
 * mismos modelos al mismo cliente, así que listModels() replica los
 * mismos endpoints, el mismo filtro y el mismo criterio de orden que
 * listar_modelos() del lado Python.
 *
 * PROVIDERS[...].modelos es una lista fija en el código: se desactualiza
 * en cuanto el proveedor saca un modelo nuevo. listModels() la
 * reemplaza por el catálogo real, consultado con la API key que el
 * cliente ya puso — sin republicar el .exe.
 */
const assert = require("assert");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const { listModels } = require(
  path.join(__dirname, "..", "..", "desktop", "electron", "services", "ai.cjs"));

/** Reemplaza fetch y anota cada pedido (url, headers). */
function fetchFalso(status = 200, cuerpo = {}) {
  const llamadas = [];
  const f = async (url, opciones = {}) => {
    llamadas.push({ url, headers: opciones.headers || {} });
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => cuerpo,
      text: async () => JSON.stringify(cuerpo),
    };
  };
  f.llamadas = llamadas;
  return f;
}

const previoFetch = global.fetch;
function restaurarFetch() { global.fetch = previoFetch; }

(async () => {
  console.log("\n== El cliente ve los modelos reales de su cuenta (Electron) ==");

  await test("ANTHROPIC: pide con x-api-key y devuelve los ids, más nuevo primero", async () => {
    global.fetch = fetchFalso(200, { data: [
      { id: "claude-haiku-4-5-20251001", created_at: "2025-10-01T00:00:00Z" },
      { id: "claude-opus-4-8", created_at: "2026-01-15T00:00:00Z" },
    ] });
    try {
      const modelos = await listModels("anthropic", "sk-ant-x");
      assert.deepStrictEqual(modelos, ["claude-opus-4-8", "claude-haiku-4-5-20251001"]);
      assert.strictEqual(global.fetch.llamadas[0].headers["x-api-key"], "sk-ant-x",
        "no mandó la API key en el header que Anthropic espera");
      assert.match(global.fetch.llamadas[0].url, /anthropic\.com/);
    } finally { restaurarFetch(); }
  });

  await test("OPENAI: filtra embeddings/whisper/tts y ordena por fecha de creación", async () => {
    global.fetch = fetchFalso(200, { data: [
      { id: "text-embedding-3-small", created: 100 },
      { id: "gpt-4o-mini", created: 200 },
      { id: "whisper-1", created: 300 },
      { id: "gpt-4.1", created: 400 },
    ] });
    try {
      const modelos = await listModels("openai", "sk-x");
      assert.deepStrictEqual(modelos, ["gpt-4.1", "gpt-4o-mini"], `no filtró/ordenó bien: ${modelos}`);
      assert.strictEqual(global.fetch.llamadas[0].headers.Authorization, "Bearer sk-x");
      assert.strictEqual(global.fetch.llamadas[0].url, "https://api.openai.com/v1/models");
    } finally { restaurarFetch(); }
  });

  await test("GROQ y los demás OpenAI-compatibles usan su propia base URL", async () => {
    global.fetch = fetchFalso(200, { data: [{ id: "llama-3.3-70b-versatile", created: 1 }] });
    try {
      await listModels("groq", "gsk-x");
      assert.strictEqual(global.fetch.llamadas[0].url, "https://api.groq.com/openai/v1/models");
    } finally { restaurarFetch(); }
  });

  await test("GEMINI: solo generateContent, sin el prefijo 'models/'", async () => {
    global.fetch = fetchFalso(200, { models: [
      { name: "models/text-embedding-004", supportedGenerationMethods: ["embedContent"] },
      { name: "models/gemini-2.5-pro", supportedGenerationMethods: ["generateContent"] },
      { name: "models/gemini-2.0-flash", supportedGenerationMethods: ["generateContent", "countTokens"] },
    ] });
    try {
      const modelos = await listModels("gemini", "AIza-x");
      assert.deepStrictEqual(modelos, ["gemini-2.5-pro", "gemini-2.0-flash"]);
      assert.match(global.fetch.llamadas[0].url, /key=AIza-x/);
    } finally { restaurarFetch(); }
  });

  await test("OLLAMA: no pide API key y usa localhost por defecto", async () => {
    global.fetch = fetchFalso(200, { models: [
      { name: "llama3.1", modified_at: "2026-01-01T00:00:00Z" },
      { name: "qwen2.5-coder", modified_at: "2026-03-01T00:00:00Z" },
    ] });
    try {
      const modelos = await listModels("ollama", null);
      assert.deepStrictEqual(modelos, ["qwen2.5-coder", "llama3.1"]);
      assert.strictEqual(global.fetch.llamadas[0].url, "http://localhost:11434/api/tags");
    } finally { restaurarFetch(); }
  });

  await test("OLLAMA remoto: respeta la Base URL que puso el cliente", async () => {
    global.fetch = fetchFalso(200, { models: [{ name: "sqlcoder", modified_at: "x" }] });
    try {
      await listModels("ollama", null, "http://192.168.1.50:11434");
      assert.strictEqual(global.fetch.llamadas[0].url, "http://192.168.1.50:11434/api/tags");
    } finally { restaurarFetch(); }
  });

  await test("CUSTOM funciona con la Base URL propia", async () => {
    global.fetch = fetchFalso(200, { data: [{ id: "mi-modelo-propio", created: 1 }] });
    try {
      const modelos = await listModels("custom", "x", "https://miendpoint.com/v1");
      assert.deepStrictEqual(modelos, ["mi-modelo-propio"]);
      assert.strictEqual(global.fetch.llamadas[0].url, "https://miendpoint.com/v1/models");
    } finally { restaurarFetch(); }
  });

  await test("CUSTOM sin Base URL no sale a ningún lado", async () => {
    global.fetch = fetchFalso(200, { data: [] });
    try {
      await assert.rejects(() => listModels("custom", "x"));
      assert.strictEqual(global.fetch.llamadas.length, 0,
        "salió a la red sin saber a quién preguntarle");
    } finally { restaurarFetch(); }
  });

  await test("AZURE no tiene listado por API: rechaza con una explicación", async () => {
    global.fetch = fetchFalso();
    try {
      await assert.rejects(
        () => listModels("azure", "x", "https://r.openai.azure.com"),
        /deployment/i);
      assert.strictEqual(global.fetch.llamadas.length, 0,
        "azure no tiene API de listado: no debería haber salido a la red");
    } finally { restaurarFetch(); }
  });

  await test("SIN API KEY no sale ni un pedido a la red", async () => {
    global.fetch = fetchFalso(200, { data: [{ id: "gpt-4o", created: 1 }] });
    try {
      await assert.rejects(() => listModels("openai", ""));
      assert.strictEqual(global.fetch.llamadas.length, 0,
        "salió a pedir el listado sin tener con qué autenticarse");
    } finally { restaurarFetch(); }
  });

  await test("un proveedor con solo modelos no-chat devuelve lista vacía, no una excepción", async () => {
    global.fetch = fetchFalso(200, { data: [{ id: "text-embedding-3-small", created: 1 }] });
    try {
      const modelos = await listModels("openai", "x");
      assert.deepStrictEqual(modelos, []);
    } finally { restaurarFetch(); }
  });

  await test("un 401 del proveedor se traduce a un mensaje accionable", async () => {
    global.fetch = fetchFalso(401, {});
    try {
      await assert.rejects(() => listModels("openai", "key-vencida"), /API key/);
    } finally { restaurarFetch(); }
  });

  await test("proveedor desconocido no revienta con un TypeError", async () => {
    global.fetch = fetchFalso();
    try {
      await assert.rejects(() => listModels("proveedor-que-no-existe", "x"), /desconocido/i);
    } finally { restaurarFetch(); }
  });

  await test("Electron y Python filtran los mismos ids no-chat", () => {
    // Los dos catálogos tienen que coincidir: si Electron muestra
    // 'whisper-1' como elegible y Python no, el mismo cliente ve listas
    // distintas según qué versión del producto abrió.
    const fs = require("fs");
    const aiSrc = fs.readFileSync(
      path.join(__dirname, "..", "..", "desktop", "electron", "services", "ai.cjs"), "utf8");
    const pySrc = fs.readFileSync(
      path.join(__dirname, "..", "..", "app-python", "proveedores_ia.py"), "utf8");
    const soloIds = (s) => (s.match(/"[a-z0-9.-]+"/g) || []).map((x) => x.replace(/"/g, ""));
    const jsBlacklist = soloIds(aiSrc.slice(aiSrc.indexOf("const NO_CHAT"), aiSrc.indexOf("];", aiSrc.indexOf("const NO_CHAT"))));
    const pyBlacklist = soloIds(pySrc.slice(pySrc.indexOf("_NO_CHAT ="), pySrc.indexOf(")", pySrc.indexOf("_NO_CHAT ="))));
    assert.deepStrictEqual([...jsBlacklist].sort(), [...pyBlacklist].sort(),
      `las listas de exclusión divergieron: JS=${jsBlacklist} PY=${pyBlacklist}`);
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
