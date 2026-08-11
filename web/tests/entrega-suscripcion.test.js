/**
 * Entrega de la SUSCRIPCIÓN: que quien paga un plan mensual reciba su licencia.
 *
 * Por qué existe este archivo. `verify-and-issue` sólo entendía `payment_id`,
 * que es lo que MercadoPago devuelve para un pago único. Una suscripción vuelve
 * con `preapproval_id`, así que el endpoint cortaba con 400 "Falta payment_id"
 * y el webhook era sólo logging. Resultado: los tres planes de la home
 * (Personal, Profesional, Empresa) debitaban la tarjeta todos los meses y el
 * cliente no recibía licencia ni descarga. Sólo andaban los packs de créditos.
 *
 * `suscripcion.test.js` cubría la CREACIÓN de la suscripción y pasaba en verde;
 * nadie cubría la ENTREGA. El bug vivía justo en ese hueco.
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
const { verifyLicense } = require(path.join(API, "_license.js"));

// Estado de la preaprobación que devuelve el MercadoPago simulado.
let subSimulada = null;
global.fetch = async (url) => {
  if (String(url).includes("/preapproval/")) {
    if (!subSimulada) return { ok: false, status: 404, json: async () => ({ message: "not found" }) };
    return { ok: true, status: 200, json: async () => subSimulada };
  }
  return { ok: true, status: 200, json: async () => ({}) };
};

const verificar = require(path.join(API, "verify-and-issue.js"));

(async () => {
  console.log("\n== Entrega de la suscripción (preapproval) ==");

  await test("una suscripción autorizada emite la licencia del plan comprado", async () => {
    subSimulada = {
      id: "2c938084726fca480172750000000000",
      status: "authorized",
      external_reference: "profesional:suscripcion:cliente@ejemplo.com",
      payer_email: "cliente@ejemplo.com",
    };
    const r = await llamar(verificar, { preapproval_id: subSimulada.id });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.ok(r.body.token, "no emitió ninguna licencia");
    const claims = verifyLicense(r.body.token);
    assert.strictEqual(claims.plan, "profesional");
    assert.strictEqual(claims.mode, "suscripcion");
    assert.strictEqual(claims.email, "cliente@ejemplo.com");
  });

  await test("el id de preapproval queda atado a la licencia (evita re-emisión)", async () => {
    subSimulada = {
      id: "2c938084726fca480172750000000001",
      status: "authorized",
      external_reference: "personal:suscripcion:otro@ejemplo.com",
      payer_email: "otro@ejemplo.com",
    };
    const r = await llamar(verificar, { preapproval_id: subSimulada.id });
    const claims = verifyLicense(r.body.token);
    assert.strictEqual(claims.jti, subSimulada.id);
  });

  await test("una suscripción pendiente NO emite licencia", async () => {
    subSimulada = {
      id: "2c938084726fca480172750000000002",
      status: "pending",
      external_reference: "empresa:suscripcion:x@y.com",
      payer_email: "x@y.com",
    };
    const r = await llamar(verificar, { preapproval_id: subSimulada.id });
    assert.strictEqual(r.statusCode, 402);
    assert.ok(!r.body.token);
  });

  await test("una suscripción cancelada NO emite licencia", async () => {
    subSimulada = {
      id: "2c938084726fca480172750000000003",
      status: "cancelled",
      external_reference: "empresa:suscripcion:x@y.com",
      payer_email: "x@y.com",
    };
    const r = await llamar(verificar, { preapproval_id: subSimulada.id });
    assert.strictEqual(r.statusCode, 402);
    assert.ok(!r.body.token);
  });

  await test("los ids de preapproval son alfanuméricos, no numéricos", async () => {
    // Validar con \d (como los payment_id) rechazaba todo id de suscripción
    // real, que es un hash. Este test fija ese contrato.
    subSimulada = {
      id: "abc123DEF456",
      status: "authorized",
      external_reference: "personal:suscripcion:a@b.com",
      payer_email: "a@b.com",
    };
    const r = await llamar(verificar, { preapproval_id: "abc123DEF456" });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  await test("un preapproval_id con formato inválido se rechaza sin llamar a MercadoPago", async () => {
    const r = await llamar(verificar, { preapproval_id: "../../etc/passwd" });
    assert.strictEqual(r.statusCode, 400);
  });

  await test("sin ningún identificador, el error nombra las dos opciones", async () => {
    const r = await llamar(verificar, {});
    assert.strictEqual(r.statusCode, 400);
    assert.ok(/preapproval_id/.test(r.body.error),
      `el mensaje debería mencionar preapproval_id: ${r.body.error}`);
  });

  await test("el pago único sigue funcionando (no se rompió el camino que andaba)", async () => {
    // El camino de pago único usa el SDK, no fetch: se simula el módulo.
    const rutaMp = require.resolve(path.join(API, "_mp.js"));
    const originalMp = require.cache[rutaMp];
    require.cache[rutaMp] = {
      id: rutaMp, filename: rutaMp, loaded: true,
      exports: {
        client: () => ({}),
        Preference: class {},
        Payment: class {
          async get() {
            return {
              id: 123456789, status: "approved",
              external_reference: "personal:credits:pago@ejemplo.com",
              payer: { email: "pago@ejemplo.com" },
            };
          }
        },
      },
    };
    delete require.cache[require.resolve(path.join(API, "verify-and-issue.js"))];
    const verificarFresco = require(path.join(API, "verify-and-issue.js"));
    try {
      const r = await llamar(verificarFresco, { payment_id: "123456789" });
      assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
      const claims = verifyLicense(r.body.token);
      assert.strictEqual(claims.plan, "personal");
      assert.strictEqual(claims.mode, "credits");
    } finally {
      if (originalMp) require.cache[rutaMp] = originalMp; else delete require.cache[rutaMp];
      delete require.cache[require.resolve(path.join(API, "verify-and-issue.js"))];
    }
  });

  console.log(`\n  ${pasadas} pasadas, ${falladas} falladas`);
  if (falladas) process.exit(1);
})();
