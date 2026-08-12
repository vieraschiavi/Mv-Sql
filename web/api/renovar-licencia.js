// MV SQL NLP — GET /api/renovar-licencia?token=...
// ====================================================================
// Devuelve una licencia nueva si la suscripción del cliente SIGUE PAGA.
//
// Por qué existe: una suscripción cobra todos los meses, pero la licencia
// se emitía una sola vez y con 365 días de vigencia. Las dos mitades de
// eso están mal y en direcciones opuestas:
//
//   - Quien cancela al segundo mes se queda con el producto un año.
//   - Y si se acortara la vigencia al ciclo de cobro sin una vía de
//     renovación, el cliente que SÍ paga perdería el acceso al mes.
//
// Lo segundo es peor que lo primero, así que el orden importa: primero
// tiene que existir la renovación, y recién después se puede acortar la
// vigencia (una línea en _license.js). Este endpoint es esa primera
// mitad, y es puramente aditivo: sin él, todo sigue funcionando como
// hasta ahora.
//
// Cómo se autentica: con el token de la licencia que el cliente ya tiene
// (viaja dentro de licencia_mvsql.json). Se acepta VENCIDO a propósito —
// renovar es justamente lo que hace alguien cuya licencia caducó. Lo que
// no se acepta nunca es un token con la firma rota.
//
// Y no se confía en el token para decidir: el token dice quién es, y a
// MercadoPago se le pregunta si todavía está pagando.
// ====================================================================
const { issueLicense, verifyLicense } = require("./_license.js");
const { archivoLicencia } = require("./_licencia-archivo.js");
const { limitar } = require("./_guard.js");

/** Consulta el estado de una suscripción en MercadoPago. */
async function traerPreapproval(id) {
  const accessToken = process.env.MP_ACCESS_TOKEN;
  if (!accessToken) throw new Error("Falta MP_ACCESS_TOKEN.");
  const r = await fetch(`https://api.mercadopago.com/preapproval/${encodeURIComponent(id)}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await r.json();
  if (!r.ok) {
    const e = new Error(data.message || "MercadoPago rechazó la consulta.");
    e.status = r.status;
    throw e;
  }
  return data;
}

module.exports = async (req, res) => {
  // Este endpoint emite licencias, así que lleva el mismo freno que los
  // demás: sin él se podría barrer tokens hasta pegarle a uno válido.
  if (!limitar(req, res, { max: 10, ventanaMs: 60_000, nombre: "renovar" })) return;

  try {
    const { token } = req.query;
    if (!token) return res.status(400).json({ error: "Falta el token de la licencia." });

    let lic;
    try {
      // ignoreExpiration: renovar es lo que hace alguien cuya licencia
      // venció. La firma sí se verifica — eso es lo que prueba que la
      // licencia la emitimos nosotros.
      lic = verifyLicense(token, { ignoreExpiration: true });
    } catch {
      return res.status(401).json({ error: "La licencia no es válida." });
    }

    // El jti es el id de MercadoPago que originó la licencia. Los de
    // suscripción son alfanuméricos; los de pago único, numéricos. Un
    // pago único no se renueva: se compró una vez y ya se entregó.
    const idMp = String(lic.jti || "");
    if (!idMp) return res.status(400).json({ error: "La licencia no tiene referencia de pago." });
    if (/^\d+$/.test(idMp)) {
      return res.status(409).json({
        error: "Esta licencia es de un pago único, no de una suscripción: no se renueva.",
      });
    }

    let sub;
    try {
      sub = await traerPreapproval(idMp);
    } catch (e) {
      if (e.status === 404) {
        return res.status(404).json({ error: "No se encontró la suscripción." });
      }
      throw e;
    }

    // "authorized" es el único estado que significa que sigue pagando.
    // "paused" y "cancelled" no renuevan — es justamente el caso que hoy
    // se estaba regalando.
    if (sub.status !== "authorized") {
      return res.status(402).json({
        error: "La suscripción no está activa.", status: sub.status,
      });
    }

    // Se re-emite con los datos de la suscripción viva, no con los del
    // token: si el cliente cambió de plan, lo que vale es lo que está
    // pagando ahora.
    const [planSub, , emailSub] = String(sub.external_reference || "").split(":");
    const email = emailSub || sub.payer_email || lic.email || "";
    const plan = planSub || lic.plan;
    const nuevo = issueLicense({ email, plan, mode: "own_ai", paymentId: sub.id });

    res.status(200).json({
      token: nuevo,
      plan,
      mode: "own_ai",
      email,
      // El archivo completo, listo para que la app lo guarde tal cual
      // encima del suyo. Devolver solo el token obligaría a cada cliente
      // a reconstruir el JSON —y a acertarle a `vence`, sin el cual la
      // licencia recién renovada nace muerta y el que paga ve el cartel
      // de "comprá tu licencia" justo después de renovar bien.
      licencia: archivoLicencia(nuevo, verifyLicense(nuevo), req.headers.host),
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
