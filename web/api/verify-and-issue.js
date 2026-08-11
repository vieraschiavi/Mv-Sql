// MV SQL NLP — GET /api/verify-and-issue?payment_id=... | ?preapproval_id=...
// Llamado desde /gracias tras volver de MercadoPago. Verifica EN VIVO contra la
// API de MercadoPago (nunca confía solo en el query string) y, si está
// aprobado, emite el token de licencia/descarga.
//
// Los dos caminos existen porque MercadoPago devuelve identificadores distintos
// según el tipo de compra, y este endpoint sólo entendía el primero:
//
//   - Pago único (preference)   → vuelve con `payment_id` / `collection_id`
//   - Suscripción (preapproval) → vuelve con `preapproval_id`
//
// Los tres planes que se anuncian en la home (Personal, Profesional, Empresa)
// son suscripciones. Al no manejar `preapproval_id`, este endpoint cortaba con
// 400 "Falta payment_id" y el cliente quedaba con la suscripción activa —
// debitándose todos los meses— y sin licencia ni descarga. Sólo funcionaban
// los packs de créditos, que sí son pago único.
const { client, Payment } = require("./_mp.js");
const { issueLicense } = require("./_license.js");
const { limitar } = require("./_guard.js");

// Una suscripción recién autorizada todavía no tiene un pago acreditado, así
// que el estado que habilita la entrega es "authorized", no "approved".
async function traerPreaprobacion(id) {
  const accessToken = process.env.MP_ACCESS_TOKEN;
  if (!accessToken) throw new Error("Falta configurar MP_ACCESS_TOKEN en las variables de entorno de Vercel.");
  const r = await fetch(`https://api.mercadopago.com/preapproval/${encodeURIComponent(id)}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await r.json();
  if (!r.ok) {
    const e = new Error(data?.message || "MercadoPago no devolvió la suscripción.");
    e.mpStatus = r.status;
    throw e;
  }
  return data;
}

module.exports = async (req, res) => {
  // Este endpoint emite licencias a partir de un payment_id y nada más:
  // no pide ninguna prueba de que quien llama sea el comprador. Los IDs
  // de MercadoPago son numéricos y correlativos, así que sin freno se
  // pueden barrer hasta pegarle a un pago aprobado y quedarse con la
  // licencia (y con los créditos de IA) de otro cliente.
  if (!limitar(req, res, { max: 10, ventanaMs: 60_000, nombre: "verify" })) return;
  try {
    const paymentId = req.query.payment_id || req.query.collection_id;
    const preapprovalId = req.query.preapproval_id;

    if (!paymentId && !preapprovalId) {
      return res.status(400).json({ error: "Falta payment_id o preapproval_id." });
    }

    let plan, mode, email, referencia, idOrigen;

    if (preapprovalId) {
      // Camino de suscripción. Los ids de preapproval son alfanuméricos
      // (hash), no numéricos como los de pago: validar con \d los rechazaba.
      if (!/^[A-Za-z0-9]{1,64}$/.test(String(preapprovalId))) {
        return res.status(400).json({ error: "preapproval_id inválido." });
      }
      const sub = await traerPreaprobacion(preapprovalId);
      if (sub.status !== "authorized") {
        return res.status(402).json({
          error: "La suscripción todavía no está autorizada.", status: sub.status,
        });
      }
      referencia = sub.external_reference;
      idOrigen = sub.id;
      email = sub.payer_email;
    } else {
      if (!/^\d{1,20}$/.test(String(paymentId))) {
        return res.status(400).json({ error: "payment_id inválido." });
      }
      const payment = await new Payment(client()).get({ id: paymentId });
      if (payment.status !== "approved") {
        return res.status(402).json({ error: "El pago todavía no está aprobado.", status: payment.status });
      }
      referencia = payment.external_reference;
      idOrigen = payment.id;
      email = payment.payer?.email;
    }

    const partes = String(referencia || "").split(":");
    plan = partes[0];
    mode = partes[1];
    const emailRef = partes[2];
    if (!plan || !mode) return res.status(400).json({ error: "Referencia de pago inválida." });

    const token = issueLicense({
      email: emailRef || email || "",
      plan, mode, paymentId: idOrigen,
    });
    res.status(200).json({ token, plan, mode, email: emailRef || email || "" });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
