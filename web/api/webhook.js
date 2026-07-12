// MV SQL NLP — POST /api/webhook (notificación IPN de MercadoPago)
// Solo logging/reconciliación: la entrega real ocurre en verify-and-issue,
// que re-verifica el pago en vivo cuando el comprador vuelve a /gracias.
// Igual respondemos 200 siempre para que MercadoPago no reintente en loop.
const { client, Payment } = require("./_mp.js");

module.exports = async (req, res) => {
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
