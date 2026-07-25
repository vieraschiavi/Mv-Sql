// MV SQL NLP — POST /api/create-subscription { plan, email }
// Crea una suscripción mensual (preapproval de MercadoPago) y devuelve el
// link de pago. A diferencia de una preferencia, esto cobra todos los meses
// hasta que el cliente cancela: es lo que hace que los clientes se acumulen.
const { SUSCRIPCIONES } = require("./_products.js");

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido." });

  const accessToken = process.env.MP_ACCESS_TOKEN;
  if (!accessToken) return res.status(500).json({ error: "Falta MP_ACCESS_TOKEN." });

  try {
    const { plan, email } = req.body || {};
    const clave = `${plan}:suscripcion`;
    const producto = SUSCRIPCIONES[clave];
    if (!producto) return res.status(400).json({ error: "Plan de suscripción inválido." });
    if (!email || !/^\S+@\S+\.\S+$/.test(email)) {
      return res.status(400).json({ error: "Ingresá un email válido." });
    }

    const origin = `https://${req.headers.host}`;
    // El SDK de MercadoPago no cubre preapproval de forma estable entre
    // versiones, así que se usa la API REST directo.
    const r = await fetch("https://api.mercadopago.com/preapproval", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        reason: producto.title,
        external_reference: `${plan}:suscripcion:${email}`,
        payer_email: email,
        back_url: `${origin}/gracias`,
        status: "pending",
        auto_recurring: {
          frequency: producto.frequency,
          frequency_type: producto.frequency_type,
          transaction_amount: producto.price,   // siempre del catálogo del servidor
          currency_id: "USD",
        },
      }),
    });

    const data = await r.json();
    if (!r.ok) {
      return res.status(r.status).json({
        error: data.message || "MercadoPago rechazó la suscripción.",
      });
    }
    res.status(200).json({ init_point: data.init_point, id: data.id });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
