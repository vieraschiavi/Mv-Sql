/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — POST /api/create-preference { plan, mode, email }
// Crea una preferencia de Checkout Pro y devuelve la URL de pago.
const { client, Preference } = require("./_mp.js");
const { PRODUCTS, esRecurrente } = require("./_products.js");
const { emailValido, limitar } = require("./_guard.js");
const { avisarIntentoDeCompra } = require("./_aviso-compra.js");

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido." });
  if (!limitar(req, res, { max: 10, ventanaMs: 60_000, nombre: "pref" })) return;
  try {
    const { plan, mode, email } = req.body || {};
    const clave = `${plan}:${mode}`;
    const product = PRODUCTS[clave];
    if (!product) return res.status(400).json({ error: "Plan o modalidad inválidos." });
    // Las suscripciones se cobran por /api/create-subscription (preapproval).
    // Si entraran por acá se cobrarían UNA sola vez: el bug que arruina el
    // negocio, cobrado como si fuera una venta buena.
    if (esRecurrente(clave)) {
      return res.status(400).json({
        error: "Este plan es una suscripción mensual: usá /api/create-subscription.",
      });
    }
    // El email termina dentro de external_reference y se muestra después
    // en el panel del dueño: si acá entra HTML, allá se renderiza.
    if (!emailValido(email)) {
      return res.status(400).json({ error: "Ingresá un email válido." });
    }

    const origin = `https://${req.headers.host}`;
    // En paralelo con la creación de la preferencia: el aviso nunca puede
    // sumar latencia extra al checkout, y avisarIntentoDeCompra() ya se
    // traga cualquier error (Resend caído, sin RESEND_API_KEY) por dentro.
    const aviso = avisarIntentoDeCompra({ plan, modo: mode, email, producto: product });
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
    await aviso;
    res.status(200).json({ init_point: preference.init_point });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
