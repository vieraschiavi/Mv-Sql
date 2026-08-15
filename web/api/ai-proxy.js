/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — POST /api/ai-proxy { token, system, user, max_tokens }
// Usado por la app (proveedor "MV SQL Créditos") cuando el cliente compró
// el modo "créditos embebidos": nosotros ponemos la IA, autenticada por el
// token de licencia, y descontamos consumo.
//
// El descuento de créditos requiere estado persistente entre llamadas: se usa
// Vercel KV (Storage → KV en el dashboard del proyecto).
//
// SIN KV el endpoint responde 503 y NO llama a la IA. Es a propósito: sin
// contador no hay tope, y sin tope una sola licencia de 100 créditos puede
// consumir la API key del dueño sin límite. Ante la duda, se corta el
// servicio, nunca la billetera.
const { verifyLicense } = require("./_license.js");
const { limitar } = require("./_guard.js");

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
  if (!limitar(req, res, { max: 60, ventanaMs: 60_000, nombre: "aiproxy" })) return;
  if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido." });
  try {
    const { token, system, user, max_tokens } = req.body || {};
    if (!token || !user) return res.status(400).json({ error: "Faltan parámetros (token, user)." });

    // Techo de costo por llamada. El contador de créditos limita CUÁNTAS
    // llamadas, pero no cuánto cuesta cada una: max_tokens, system y user
    // venían del cliente sin ningún límite. Una licencia de 500 créditos
    // con max_tokens=200000 y un prompt enorme gasta, contra la tarjeta
    // del dueño, un múltiplo enorme de lo que se cobró por ese paquete —
    // y el contador lo registra como 500 llamadas normales.
    //
    // Los topes son holgados respecto del uso real del producto
    // (motor.py pide 1500-2000 tokens y manda esquema, no datos), así que
    // un cliente legítimo no los toca nunca.
    const MAX_TOKENS_TECHO = 4000;
    const MAX_CARACTERES_PROMPT = 24000;   // ~6k tokens de entrada
    const tokensPedidos = Number(max_tokens);
    const tokensSalida = Number.isFinite(tokensPedidos)
      ? Math.min(Math.max(1, Math.floor(tokensPedidos)), MAX_TOKENS_TECHO)
      : 1500;
    if (String(user).length + String(system || "").length > MAX_CARACTERES_PROMPT) {
      return res.status(413).json({
        error: "La consulta es demasiado grande para el servicio de créditos. " +
               "Usá tu propia API key desde el menú de proveedor de IA.",
      });
    }

    const license = verifyLicense(token);
    if (license.mode !== "credits") {
      return res.status(403).json({ error: "Esta licencia no tiene créditos embebidos (es modo IA propia)." });
    }

    const kv = await getKv();
    if (!kv) {
      // Fail-closed: sin contador de créditos no se sirve IA. Cambiar esto
      // por "seguir sin tope" reabre un agujero por el que se va la plata.
      console.error("[ai-proxy] Vercel KV no configurado: se rechaza el pedido " +
                    "para no servir IA sin tope de créditos.");
      return res.status(503).json({
        error: "El servicio de créditos no está disponible en este momento. " +
               "Escribinos a vieraschiavi@gmail.com o usá tu propia API key " +
               "desde el menú de proveedor de IA.",
      });
    }

    // Contador por licencia. La clave usa el jti (id del pago que originó la
    // licencia): es estable y único aunque se re-emita el mismo token.
    const idLicencia = license.jti || token.slice(-24);
    const key = `mvsql:credits:${idLicencia}`;
    // incr atómico PRIMERO, y el retorno es el número de crédito de ESTE
    // pedido. Antes se hacía get -> comparar -> incr: dos pedidos en paralelo
    // cerca del límite leían el mismo `used` y los dos pasaban, sirviendo IA
    // de más contra la billetera del dueño. Con el retorno de incr, cada
    // pedido concurrente recibe un número distinto y solo uno puede ser el
    // que cruza el tope.
    const usado = await kv.incr(key);
    if (usado > license.credits) {
      // Se pasó del tope: se devuelve el crédito que este incr tomó de más
      // (para que un burst rechazado no deje el contador inflado) y se corta.
      await kv.decr(key);
      return res.status(402).json({
        error: "Sin créditos restantes. Comprá otro paquete en mvsqlnlp.com.",
      });
    }
    const remaining = license.credits - usado;

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) return res.status(500).json({ error: "Falta configurar ANTHROPIC_API_KEY en el servidor (Vercel)." });

    // Si la IA no responde, se devuelve el crédito: que Anthropic esté caído
    // no es culpa del cliente y no debería costarle un crédito.
    let r, data;
    try {
      r = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "x-api-key": apiKey, "anthropic-version": "2023-06-01", "content-type": "application/json" },
        body: JSON.stringify({
          model: "claude-haiku-4-5-20251001",
          max_tokens: tokensSalida,
          system: system || "",
          messages: [{ role: "user", content: user }],
        }),
      });
      data = await r.json();
    } catch {
      await kv.decr(key);
      return res.status(502).json({ error: "El proveedor de IA no está disponible ahora mismo. Probá de nuevo." });
    }
    if (!r.ok) {
      await kv.decr(key);
      return res.status(r.status === 429 ? 429 : 502).json({
        error: data?.error?.message || "Error del proveedor de IA." });
    }
    const text = (data.content || []).map((b) => b.text || "").join("");
    res.status(200).json({ text, remaining });
  } catch (e) {
    // 401 solo para la falla de verifyLicense (token inválido/vencido), que
    // es la única que significa "tu licencia no sirve". Cualquier otra cosa
    // acá es un error nuestro, no un problema de la licencia del cliente:
    // devolverlo como 401 le decía "comprá de nuevo" por un bug del servidor.
    const esLicencia = /jwt|token|licen|signature|expired|malformed/i.test(e.message || "");
    res.status(esLicencia ? 401 : 500).json({
      error: esLicencia ? "Licencia inválida o vencida." : "Error interno. Probá de nuevo en un momento." });
  }
};
