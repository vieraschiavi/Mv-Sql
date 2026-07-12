// MV SQL NLP — POST /api/create-preference { plan, mode, email }
// Crea una preferencia de Checkout Pro y devuelve la URL de pago.
const { client, Preference } = require("./_mp.js");
const { PRODUCTS } = require("./_products.js");

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido." });
  try {
    const { plan, mode, email } = req.body || {};
    const product = PRODUCTS[`${plan}:${mode}`];
    if (!product) return res.status(400).json({ error: "Plan o modalidad inválidos." });
    if (!email || !/^\S+@\S+\.\S+$/.test(email)) {
      return res.status(400).json({ error: "Ingresá un email válido." });
    }

    const origin = `https://${req.headers.host}`;
    const preference = await new Preference(client()).create({
      body: {
        items: [{
          title: product.title, quantity: 1,
          unit_price: product.price, currency_id: "USD",
        }],
        payer: { email },
        back_urls: {
          success: `${origin}/gracias`,
          failure: `${origin}/pago-fallido`,
          pending: `${origin}/pago-fallido`,
        },
        auto_return: "approved",
        external_reference: `${plan}:${mode}:${email}`,
        notification_url: `${origin}/api/webhook`,
      },
    });
    res.status(200).json({ init_point: preference.init_point });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
