// MV SQL NLP — licencias de descarga (JWT firmado, sin base de datos)
// El token codifica: email, plan, modo (own_ai | credits), créditos incluidos
// y el id de pago de MercadoPago que lo originó (evita re-emisión duplicada).
const jwt = require("jsonwebtoken");

const CREDITS_BY_PLAN = { personal: 100, profesional: 500, empresa: 2000 };

function secret() {
  const s = process.env.LICENSE_SECRET;
  if (!s) throw new Error("Falta configurar LICENSE_SECRET en las variables de entorno de Vercel.");
  return s;
}

function issueLicense({ email, plan, mode, paymentId }) {
  const credits = mode === "credits" ? (CREDITS_BY_PLAN[plan] || 100) : 0;
  return jwt.sign(
    { email, plan, mode, credits },
    secret(),
    { expiresIn: "365d", jwtid: String(paymentId), subject: email }
  );
}

function verifyLicense(token) {
  return jwt.verify(token, secret());
}

module.exports = { issueLicense, verifyLicense, CREDITS_BY_PLAN };
