// MV SQL NLP — POST /api/ai-proxy { token, system, user, max_tokens }
// Usado por la app (proveedor "MV SQL Créditos") cuando el cliente compró
// el modo "créditos embebidos": nosotros ponemos la IA, autenticada por el
// token de licencia, y descontamos consumo.
//
// El descuento real de créditos requiere estado persistente entre llamadas.
// Si el proyecto tiene conectado Vercel KV (Storage → KV en el dashboard),
// se usa para llevar la cuenta real. Sin KV configurado, el proxy funciona
// igual pero SIN tope server-side (documentado abajo) — conectar KV antes
// de vender en volumen.
const { verifyLicense } = require("./_license.js");

async function getKv() {
  try {
    const { kv } = require("@vercel/kv");
    // fuerza el uso para detectar temprano si las env vars no están seteadas
    if (!process.env.KV_REST_API_URL) return null;
    return kv;
  } catch {
    return null;
  }
}

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido." });
  try {
    const { token, system, user, max_tokens } = req.body || {};
    if (!token || !user) return res.status(400).json({ error: "Faltan parámetros (token, user)." });

    const license = verifyLicense(token);
    if (license.mode !== "credits") {
      return res.status(403).json({ error: "Esta licencia no tiene créditos embebidos (es modo IA propia)." });
    }

    const kv = await getKv();
    let remaining = null;
    if (kv) {
      const key = `mvsql:credits:${token.slice(-24)}`;
      const used = Number((await kv.get(key)) || 0);
      remaining = license.credits - used;
      if (remaining <= 0) {
        return res.status(402).json({ error: "Sin créditos restantes. Comprá otro paquete en mvsqlnlp.com." });
      }
      await kv.incr(key);
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) return res.status(500).json({ error: "Falta configurar ANTHROPIC_API_KEY en el servidor (Vercel)." });

    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": apiKey, "anthropic-version": "2023-06-01", "content-type": "application/json" },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: max_tokens || 1500,
        system: system || "",
        messages: [{ role: "user", content: user }],
      }),
    });
    const data = await r.json();
    if (!r.ok) {
      return res.status(r.status).json({ error: data?.error?.message || "Error del proveedor de IA." });
    }
    const text = (data.content || []).map((b) => b.text || "").join("");
    res.status(200).json({ text, remaining: kv ? remaining - 1 : null });
  } catch (e) {
    res.status(401).json({ error: e.message });
  }
};
