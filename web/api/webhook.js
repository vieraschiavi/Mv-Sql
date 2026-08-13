/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — POST /api/webhook (notificación IPN de MercadoPago)
// Solo logging/reconciliación: la entrega real ocurre en verify-and-issue,
// que re-verifica el pago en vivo cuando el comprador vuelve a /gracias.
// Igual respondemos 200 siempre para que MercadoPago no reintente en loop.
const { client, Payment } = require("./_mp.js");
const { limitar } = require("./_guard.js");

module.exports = async (req, res) => {
  // Este endpoint es público (lo llama MercadoPago sin autenticación) y por
  // cada pedido dispara una llamada saliente a la API de MercadoPago. Sin
  // freno, cualquiera puede barrerlo con "data.id" inventados y hacer que
  // paguemos ese costo/cupo — es el mismo riesgo que ya se cerró en los
  // demás endpoints públicos, solo que acá era menos obvio porque no emite
  // nada por sí mismo.
  if (!limitar(req, res, { max: 60, ventanaMs: 60_000, nombre: "webhook" })) return;
  try {
    const id = req.body?.data?.id || req.query["data.id"];
    if (id) {
      const payment = await new Payment(client()).get({ id });
      console.log("[mvsql webhook]", payment.id, payment.status, payment.external_reference);
    }
  } catch (e) {
    console.warn("[mvsql webhook] error:", e.message);
  }
  res.status(200).json({ received: true });
};
