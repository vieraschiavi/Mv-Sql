// MV SQL NLP — GET /api/verify-and-issue?payment_id=...
// Llamado desde /gracias tras volver de MercadoPago. Verifica el pago EN VIVO
// contra la API de MercadoPago (nunca confía solo en el query string) y,
// si está aprobado, emite el token de licencia/descarga.
const { client, Payment } = require("./_mp.js");
const { issueLicense } = require("./_license.js");
const { limitar } = require("./_guard.js");

module.exports = async (req, res) => {
  // Este endpoint emite licencias a partir de un payment_id y nada más:
  // no pide ninguna prueba de que quien llama sea el comprador. Los IDs
  // de MercadoPago son numéricos y correlativos, así que sin freno se
  // pueden barrer hasta pegarle a un pago aprobado y quedarse con la
  // licencia (y con los créditos de IA) de otro cliente.
  if (!limitar(req, res, { max: 10, ventanaMs: 60_000, nombre: "verify" })) return;
  try {
    const paymentId = req.query.payment_id || req.query.collection_id;
    if (!paymentId) return res.status(400).json({ error: "Falta payment_id." });
    if (!/^\d{1,20}$/.test(String(paymentId))) {
      return res.status(400).json({ error: "payment_id inválido." });
    }

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
