/** La suscripción se puede RENOVAR mientras se siga pagando.
 *
 * Una suscripción cobra todos los meses, pero la licencia se emitía una
 * sola vez y con 365 días de vigencia. Las dos mitades de eso están mal,
 * y en direcciones opuestas:
 *
 *   - Quien cancela al segundo mes se queda con el producto un año.
 *   - Y si se acortara la vigencia al ciclo de cobro SIN una vía de
 *     renovación, el cliente que sí paga perdería el acceso al mes.
 *
 * Lo segundo es peor que lo primero, así que el orden importa: primero
 * la renovación, después acortar la vigencia. Este endpoint es la primera
 * mitad, y es aditivo — sin él todo sigue funcionando como hasta ahora.
 *
 * Lo que se fija acá es que renovar NO sea una puerta trasera:
 *   - una firma rota no renueva, aunque el contenido parezca válido;
 *   - una suscripción cancelada o pausada NO renueva (es exactamente el
 *     caso que hoy se regala);
 *   - un pago único no se renueva, porque no hay nada que renovar;
 *   - y una licencia VENCIDA sí renueva, porque es el único caso que
 *     importa: rechazarla haría imposible el único camino para dejar de
 *     estar vencido.
 */
const assert = require("assert");
const path = require("path");

process.env.MP_ACCESS_TOKEN = "TEST-mp";
process.env.LICENSE_SECRET = "secreto-de-prueba";

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}
function resFalsa() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
const llamar = async (h, query) => {
  const res = resFalsa();
  await h({ method: "GET", headers: { host: "mvsqlnlp.com" }, query }, res);
  return res;
};

const API = path.join(__dirname, "..", "api");

/** Estado del preapproval que devuelve el MercadoPago falso. */
let subFalsa = null;
global.fetch = async (url) => {
  if (String(url).includes("/preapproval/")) {
    if (!subFalsa) return { ok: false, status: 404, json: async () => ({ message: "no existe" }) };
    return { ok: true, status: 200, json: async () => subFalsa };
  }
  return { ok: true, status: 200, json: async () => ({}) };
};

const renovar = require(path.join(API, "renovar-licencia.js"));
const { issueLicense, verifyLicense } = require(path.join(API, "_license.js"));
const jwt = require(path.join(__dirname, "..", "node_modules", "jsonwebtoken"));

const ID_SUB = "2c938084726fca480172750000000000";

/** Licencia de suscripción, opcionalmente ya vencida. */
function licenciaSub({ vencida = false } = {}) {
  if (!vencida) {
    return issueLicense({ email: "cliente@empresa.com", plan: "profesional",
                          mode: "own_ai", paymentId: ID_SUB });
  }
  // Emitida hace 400 días y con 1 día de vigencia: vencida de verdad.
  const hace = Math.floor(Date.now() / 1000) - 400 * 86400;
  return jwt.sign(
    { email: "cliente@empresa.com", plan: "profesional", mode: "own_ai", credits: 0, iat: hace },
    process.env.LICENSE_SECRET,
    { expiresIn: "1d", jwtid: ID_SUB, subject: "cliente@empresa.com" });
}

(async () => {
  console.log("\n== Renovación de la suscripción ==");

  await test("UNA SUSCRIPCIÓN VENCIDA PERO PAGA SE RENUEVA", () => {
    // El caso que da sentido a todo el endpoint.
    subFalsa = { id: ID_SUB, status: "authorized",
                 external_reference: "profesional:suscripcion:cliente@empresa.com",
                 payer_email: "cliente@empresa.com" };
    return llamar(renovar, { token: licenciaSub({ vencida: true }) }).then((r) => {
      assert.strictEqual(r.statusCode, 200,
        `el cliente que paga se quedó sin acceso: ${JSON.stringify(r.body)}`);
      const nueva = verifyLicense(r.body.token);
      assert.strictEqual(nueva.plan, "profesional");
      assert.strictEqual(nueva.mode, "own_ai");
      assert.ok(nueva.exp * 1000 > Date.now(), "la licencia nueva ya nace vencida");
    });
  });

  await test("UNA SUSCRIPCIÓN CANCELADA NO RENUEVA", async () => {
    // Es el caso que hoy se regala: cancela y sigue usando el producto.
    subFalsa = { id: ID_SUB, status: "cancelled",
                 external_reference: "profesional:suscripcion:x@y.com" };
    const r = await llamar(renovar, { token: licenciaSub() });
    assert.strictEqual(r.statusCode, 402);
    assert.ok(!r.body.token, "le dio licencia nueva a alguien que canceló");
  });

  await test("una suscripción pausada tampoco", async () => {
    subFalsa = { id: ID_SUB, status: "paused",
                 external_reference: "profesional:suscripcion:x@y.com" };
    const r = await llamar(renovar, { token: licenciaSub() });
    assert.strictEqual(r.statusCode, 402);
  });

  await test("UNA FIRMA ROTA NO RENUEVA, aunque el contenido parezca bien", async () => {
    // Sin esto, cualquiera se arma un token con el plan que quiera.
    subFalsa = { id: ID_SUB, status: "authorized",
                 external_reference: "empresa:suscripcion:x@y.com" };
    const falso = jwt.sign(
      { email: "x@y.com", plan: "empresa", mode: "own_ai" },
      "otra-clave-distinta", { jwtid: ID_SUB, expiresIn: "365d" });
    const r = await llamar(renovar, { token: falso });
    assert.strictEqual(r.statusCode, 401, "aceptó una licencia que no emitimos nosotros");
    assert.ok(!r.body.token);
  });

  await test("no se confía en el token: se le pregunta a MercadoPago", async () => {
    // El token dice quién es; MercadoPago dice si todavía paga.
    subFalsa = null;   // MercadoPago no conoce esa suscripción
    const r = await llamar(renovar, { token: licenciaSub() });
    assert.notStrictEqual(r.statusCode, 200);
    assert.ok(!r.body.token);
  });

  await test("un pago único no se renueva (no hay nada que renovar)", async () => {
    // Los ids de pago son numéricos; los de suscripción, alfanuméricos.
    const unico = issueLicense({ email: "x@y.com", plan: "personal",
                                 mode: "credits", paymentId: "123456789" });
    const r = await llamar(renovar, { token: unico });
    assert.strictEqual(r.statusCode, 409);
    assert.match(r.body.error, /pago único/i);
  });

  await test("sin token contesta 400, no 500", async () => {
    const r = await llamar(renovar, {});
    assert.strictEqual(r.statusCode, 400);
  });

  await test("el plan sale de la suscripción viva, no del token viejo", async () => {
    // Si el cliente cambió de plan, vale lo que está pagando ahora.
    subFalsa = { id: ID_SUB, status: "authorized",
                 external_reference: "empresa:suscripcion:cliente@empresa.com",
                 payer_email: "cliente@empresa.com" };
    const r = await llamar(renovar, { token: licenciaSub() });  // el token dice "profesional"
    assert.strictEqual(r.statusCode, 200);
    assert.strictEqual(verifyLicense(r.body.token).plan, "empresa",
      "renovó con el plan viejo: el cambio de plan no se refleja");
  });

  // ── la otra mitad: el cliente tiene que TENER el token ────────
  await test("la licencia de suscripción incluye el token (si no, no puede renovar)", () => {
    // El modo own_ai es el de las suscripciones. Antes solo la licencia
    // de créditos llevaba el token, así que el suscriptor no tenía con
    // qué acreditarse — y renovar por email dejaría que cualquiera que lo
    // conozca se lleve la licencia ajena.
    const fs = require("fs");
    const src = fs.readFileSync(path.join(API, "download.js"), "utf8");
    const ownAi = src.slice(src.indexOf('modo: "own_ai"'));
    assert.match(ownAi.slice(0, 600), /\btoken,/,
      "la licencia own_ai no lleva el token: el suscriptor no puede renovar");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
