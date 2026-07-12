// MV SQL NLP — GET /api/verify-and-issue?payment_id=...
// Llamado desde /gracias tras volver de MercadoPago. Verifica el pago EN VIVO
// contra la API de MercadoPago (nunca confía solo en el query string) y,
// si está aprobado, emite el token de licencia/descarga.
const { client, Payment } = require("./_mp.js");
const { issueLicense } = require("./_license.js");

module.exports = async (req, res) => {
  try {
    const paymentId = req.query.payment_id || req.query.collection_id;
    if (!paymentId) return res.status(400).json({ error: "Falta payment_id." });

    const payment = await new Payment(client()).get({ id: paymentId });
    if (payment.status !== "approved") {
      return res.status(402).json({ error: "El pago todavía no está aprobado.", status: payment.status });
    }

    const [plan, mode, email] = String(payment.external_reference || "").split(":");
    if (!plan || !mode) return res.status(400).json({ error: "Referencia de pago inválida." });

    const token = issueLicense({
      email: email || payment.payer?.email || "",
      plan, mode, paymentId: payment.id,
    });
    res.status(200).json({ token, plan, mode, email });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
