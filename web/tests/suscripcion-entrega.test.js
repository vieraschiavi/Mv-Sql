/* © 2026 Martín Viera. Todos los derechos reservados. */

/** La suscripción tiene que ENTREGAR, no solo cobrar.
 *
 * Los cuatro planes recurrentes (US$ 15 / 29 / 79 / 150 por mes) se cobran
 * con preapproval de MercadoPago. Un preapproval vuelve a /gracias con
 * `preapproval_id` y NO con `payment_id`: al autorizar todavía no hay un
 * pago hecho, hay una autorización de débito recurrente.
 *
 * verify-and-issue solo miraba payment_id, así que cortaba con 400 "Falta
 * payment_id" — y /gracias ni siquiera llegaba a llamarlo, porque también
 * leía solo payment_id y se quedaba en "falta el id de pago". El webhook
 * tampoco lo rescataba: es logging por diseño, dice el comentario y lo
 * confirma el código. Resultado: la tarjeta se debitaba todos los meses y
 * el cliente nunca recibía licencia ni descarga.
 *
 * Es el peor modo de falla que puede tener un cobro, porque no se parece a
 * una falla: MercadoPago dice que el pago salió bien, el dinero entra, y
 * el único que sabe que algo anda mal es el cliente que no recibió nada.
 * Ninguna métrica del lado nuestro lo muestra.
 *
 * Estos tests fijan las dos mitades: que el endpoint acepte y verifique un
 * preapproval, y que /gracias sepa mandárselo.
 */
const assert = require("assert");
const fs = require("fs");
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

/** Estado que devuelve el preapproval falso; cada test lo ajusta. */
let subFalsa = null;
global.fetch = async (url) => {
  if (String(url).includes("/preapproval/")) {
    if (!subFalsa) return { ok: false, status: 404, json: async () => ({ message: "no existe" }) };
    return { ok: true, status: 200, json: async () => subFalsa };
  }
  return { ok: true, status: 200, json: async () => ({}) };
};

const verificar = require(path.join(API, "verify-and-issue.js"));
const { verifyLicense } = require(path.join(API, "_license.js"));

(async () => {
  console.log("\n== La suscripción entrega la licencia ==");

  await test("UNA SUSCRIPCIÓN AUTORIZADA EMITE LICENCIA", async () => {
    subFalsa = {
      id: "2c938084726fca480172750000000000",
      status: "authorized",
      external_reference: "profesional:suscripcion:cliente@empresa.com",
      payer_email: "cliente@empresa.com",
    };
    const r = await llamar(verificar, { preapproval_id: subFalsa.id });
    assert.strictEqual(r.statusCode, 200,
      `el suscriptor no recibe nada: ${JSON.stringify(r.body)}`);
    assert.ok(r.body.token, "no vino el token de descarga");

    const lic = verifyLicense(r.body.token);
    assert.strictEqual(lic.plan, "profesional");
    assert.strictEqual(lic.email, "cliente@empresa.com");
    // Una suscripción es licencia con API key propia del cliente. Si saliera
    // como "credits" le estaríamos regalando créditos de IA nuestros todos
    // los meses, que es el costo que el modelo de suscripción evita.
    assert.strictEqual(lic.mode, "own_ai");
    assert.strictEqual(lic.credits, 0);
  });

  await test("los cuatro planes recurrentes entregan, no solo uno", async () => {
    const { SUSCRIPCIONES } = require(path.join(API, "_products.js"));
    for (const clave of Object.keys(SUSCRIPCIONES)) {
      const plan = clave.split(":")[0];
      subFalsa = {
        id: "abc123", status: "authorized",
        external_reference: `${plan}:suscripcion:x@y.com`, payer_email: "x@y.com",
      };
      const r = await llamar(verificar, { preapproval_id: "abc123" });
      assert.strictEqual(r.statusCode, 200, `el plan ${plan} no entrega: ${JSON.stringify(r.body)}`);
      assert.strictEqual(verifyLicense(r.body.token).plan, plan);
    }
  });

  await test("una suscripción sin autorizar NO emite licencia", async () => {
    // "pending" es el estado con el que se crea, antes de que el cliente
    // confirme. Emitir acá sería regalar el producto a quien abrió el link
    // de pago y no lo completó.
    subFalsa = { id: "abc123", status: "pending", external_reference: "personal:suscripcion:x@y.com" };
    const r = await llamar(verificar, { preapproval_id: "abc123" });
    assert.strictEqual(r.statusCode, 402);
    assert.ok(!r.body.token);
  });

  await test("una suscripción cancelada NO emite licencia", async () => {
    subFalsa = { id: "abc123", status: "cancelled", external_reference: "personal:suscripcion:x@y.com" };
    const r = await llamar(verificar, { preapproval_id: "abc123" });
    assert.strictEqual(r.statusCode, 402);
  });

  await test("no se confía en el query string: se consulta a MercadoPago", async () => {
    // Sin esto, cualquiera inventa un preapproval_id y se lleva la licencia.
    subFalsa = null;   // MercadoPago no lo conoce
    const r = await llamar(verificar, { preapproval_id: "inventado123" });
    assert.notStrictEqual(r.statusCode, 200, "emitió licencia para una suscripción inexistente");
    assert.ok(!r.body.token);
  });

  await test("un preapproval_id con formato raro se rechaza sin llamar a MP", async () => {
    const r = await llamar(verificar, { preapproval_id: "../../etc/passwd" });
    assert.strictEqual(r.statusCode, 400);
  });

  await test("el pago único sigue andando (no se rompió la rama vieja)", async () => {
    const r = await llamar(verificar, {});
    assert.strictEqual(r.statusCode, 400);
    assert.match(r.body.error, /payment_id/);
  });

  // ── la otra mitad: /gracias tiene que mandar el parámetro ─────
  await test("/gracias lee preapproval_id y se lo pasa al endpoint", () => {
    const html = fs.readFileSync(path.join(__dirname, "..", "gracias", "index.html"), "utf8");
    assert.ok(/params\.get\(["']preapproval_id["']\)/.test(html),
      "/gracias no lee preapproval_id: el suscriptor ve 'falta el id de pago'");
    assert.ok(/preapproval_id=\$\{/.test(html),
      "/gracias no le manda preapproval_id a verify-and-issue");
  });

  await test("create-subscription manda al cliente de vuelta a /gracias", () => {
    // Si el back_url apuntara a otro lado, todo lo de arriba no se ejecuta
    // nunca. Es la punta de la cadena y no la cubría ningún test.
    const src = fs.readFileSync(path.join(API, "create-subscription.js"), "utf8");
    assert.ok(/back_url:\s*`\$\{origin\}\/gracias`/.test(src),
      "el back_url de la suscripción ya no apunta a /gracias");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
