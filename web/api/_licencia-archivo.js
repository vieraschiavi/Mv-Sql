// MV SQL NLP — el CONTENIDO de licencia_mvsql.json, en un solo lugar
// ====================================================================
// Este archivo es el que la app (Electron y Python) lee para saber si
// alguien pagó. Lo escriben dos endpoints distintos:
//
//   - /api/download        cuando el cliente compra y baja el producto;
//   - /api/renovar-licencia cuando su suscripción sigue paga y la app
//     pide una licencia nueva sola, sin que el cliente haga nada.
//
// Si cada uno armara el objeto por su cuenta, el segundo podría emitir
// una licencia a la que le falte un campo que el primero sí pone — y el
// que se nota tarde es `vence`: sin él, `vigente()` da false y la
// licencia recién renovada nace muerta. El cliente que paga vería el
// cartel de "comprá tu licencia" JUSTO después de una renovación
// exitosa, que es la peor forma posible de fallar.
//
// Por eso el objeto se arma acá una sola vez y los dos endpoints lo
// usan. La forma no puede divergir porque no hay dos formas.
// ====================================================================

/**
 * Arma el JSON que se guarda como licencia_mvsql.json.
 *
 * @param {string} token   el JWT firmado (viaja adentro: es lo único con
 *                         lo que el cliente puede acreditarse para renovar)
 * @param {object} license el payload ya verificado de ese token
 * @param {string} [host]  host de la API, solo para el modo créditos
 */
function archivoLicencia(token, license, host) {
  const esCredits = license.mode === "credits";
  const base = {
    producto: "MV SQL NLP",
    email: license.email,
    plan: license.plan,
    modo: esCredits ? "credits" : "own_ai",
    // El token va en las DOS variantes, no solo en la de créditos. Es lo
    // único que el cliente tiene para acreditarse ante
    // /api/renovar-licencia: renovar por email dejaría que cualquiera
    // que lo conozca se lleve la licencia ajena.
    token,
    emitida: new Date(license.iat * 1000).toISOString(),
    vence: new Date(license.exp * 1000).toISOString(),
  };

  if (esCredits) {
    return {
      ...base,
      creditos: license.credits,
      proxy_url: `https://${host}/api/ai-proxy`,
      nota: "No compartas este archivo: contiene tu token de créditos. Elegí el proveedor 'MV SQL Créditos' en la app — no hace falta ninguna API key.",
    };
  }
  return {
    ...base,
    nota: "No compartas este archivo: acredita tu licencia paga. Configurá tu propia API key en 'Proveedor de IA' — este archivo solo te exime del límite de la prueba gratuita.",
  };
}

module.exports = { archivoLicencia };
