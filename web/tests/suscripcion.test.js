/** Suscripciones (preapproval) y tope de créditos del proxy de IA. */
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
const llamar = async (h, req) => {
  const res = resFalsa();
  await h({ method: "POST", headers: { host: "mvsqlnlp.com" }, body: {}, query: {}, ...req }, res);
  return res;
};

const API = path.join(__dirname, "..", "api");
const { SUSCRIPCIONES, esRecurrente } = require(path.join(API, "_products.js"));

let ultimoBody = null;
global.fetch = async (url, opts) => {
  ultimoBody = JSON.parse(opts.body);
  if (String(url).includes("/preapproval")) {
    return { ok: true, status: 200,
             json: async () => ({ init_point: "https://mp.test/suscribir", id: "sub_1" }) };
  }
  return { ok: true, status: 200, json: async () => ({ content: [{ text: "ok" }] }) };
};
const crearSuscripcion = require(path.join(API, "create-subscription.js"));

(async () => {
  console.log("\n== Suscripciones (cobro recurrente) ==");

  await test("crea la suscripción con el precio y la frecuencia del catálogo", async () => {
    const r = await llamar(crearSuscripcion, { body: { plan: "profesional", email: "a@b.com" } });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.ok(r.body.init_point);
    assert.strictEqual(ultimoBody.auto_recurring.transaction_amount,
      SUSCRIPCIONES["profesional:suscripcion"].price);
    assert.strictEqual(ultimoBody.auto_recurring.frequency, 1);
    assert.strictEqual(ultimoBody.auto_recurring.frequency_type, "months");
  });

  await test("ignora un precio inyectado desde el cliente", async () => {
    await llamar(crearSuscripcion, { body: { plan: "empresa", email: "a@b.com",
      price: 1, transaction_amount: 1, auto_recurring: { transaction_amount: 1 } } });
    assert.strictEqual(ultimoBody.auto_recurring.transaction_amount, 79);
  });

  await test("rechaza plan de suscripción inexistente", async () => {
    const r = await llamar(crearSuscripcion, { body: { plan: "gratis", email: "a@b.com" } });
    assert.strictEqual(r.statusCode, 400);
  });

  await test("rechaza email inválido", async () => {
    const r = await llamar(crearSuscripcion, { body: { plan: "personal", email: "nope" } });
    assert.strictEqual(r.statusCode, 400);
  });

  await test("el retainer de soporte también es recurrente", async () => {
    const r = await llamar(crearSuscripcion, { body: { plan: "soporte", email: "a@b.com" } });
    assert.strictEqual(r.statusCode, 200);
    assert.strictEqual(ultimoBody.auto_recurring.transaction_amount, 150);
  });

  await test("esRecurrente distingue suscripción de pago único", async () => {
    assert.ok(esRecurrente("profesional:suscripcion"));
    assert.ok(!esRecurrente("implementacion:servicio"));
    assert.ok(!esRecurrente("personal:credits"));
  });

  console.log("\n== Tope de créditos: el proxy falla cerrado ==");

  const jwt = require("jsonwebtoken");
  const licenciaCreditos = jwt.sign(
    { email: "c@t.com", plan: "personal", mode: "credits", credits: 100 },
    process.env.LICENSE_SECRET, { expiresIn: "365d", jwtid: "pago_1" });

  await test("SIN Vercel KV no sirve IA (no regala la API key del dueño)", async () => {
    delete process.env.KV_REST_API_URL;
    delete require.cache[require.resolve(path.join(API, "ai-proxy.js"))];
    const proxy = require(path.join(API, "ai-proxy.js"));
    const r = await llamar(proxy, { body: { token: licenciaCreditos, user: "hola" } });
    assert.strictEqual(r.statusCode, 503,
      "sin contador de créditos hay que cortar el servicio, no la billetera");
  });

  await test("rechaza una licencia de IA propia en el proxy de créditos", async () => {
    const propia = jwt.sign({ email: "c@t.com", plan: "personal", mode: "own_ai", credits: 0 },
      process.env.LICENSE_SECRET, { expiresIn: "365d", jwtid: "pago_2" });
    delete require.cache[require.resolve(path.join(API, "ai-proxy.js"))];
    const proxy = require(path.join(API, "ai-proxy.js"));
    const r = await llamar(proxy, { body: { token: propia, user: "hola" } });
    assert.strictEqual(r.statusCode, 403);
  });

  await test("rechaza un token falsificado", async () => {
    const falso = jwt.sign({ email: "h@x.com", mode: "credits", credits: 99999 },
      "otro-secreto", { expiresIn: "365d" });
    delete require.cache[require.resolve(path.join(API, "ai-proxy.js"))];
    const proxy = require(path.join(API, "ai-proxy.js"));
    const r = await llamar(proxy, { body: { token: falso, user: "hola" } });
    assert.strictEqual(r.statusCode, 401);
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
