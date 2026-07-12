// MV SQL NLP — cliente de MercadoPago (Checkout Pro)
const { MercadoPagoConfig, Preference, Payment } = require("mercadopago");

function client() {
  const accessToken = process.env.MP_ACCESS_TOKEN;
  if (!accessToken) {
    throw new Error("Falta configurar MP_ACCESS_TOKEN en las variables de entorno de Vercel.");
  }
  return new MercadoPagoConfig({ accessToken });
}

module.exports = { client, Preference, Payment };
