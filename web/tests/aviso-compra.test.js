/* © 2026 Martín Viera. Todos los derechos reservados. */

/** Aviso de intención de compra: create-preference y create-subscription
 * tienen que avisar por mail al dueño apenas alguien genera el link de
 * pago (antes de que MercadoPago confirme nada) — así puede activar un
 * plan pago (p.ej. Vercel Pro) solo cuando aparece intención de compra
 * real, en vez de pagarlo a ciegas.
 *
 * Lo crítico a probar acá no es que el mail salga: es que si Resend falla
 * o no está configurado, EL COBRO SIGUE FUNCIONANDO IGUAL. Un aviso es un
 * extra, nunca puede tumbar un checkout.
 */
const assert = require("assert");
const path = require("path");
const Module = require("module");

process.env.MP_ACCESS_TOKEN = "TEST-mp";
process.env.LICENSE_SECRET = "secreto-de-prueba";

let mails = [];
const mockResend = {
  enviarMail: async (datos) => { mails.push(datos); return { id: "mail_" + mails.length }; },
};
const mockMP = {
  client: () => ({}),
  Preference: class {
    async create({ body }) {
      mockMP.ultimaPreferencia = body;
      return { init_point: "https://mp.test/checkout/abc", id: "pref_1" };
    }
  },
};

const cargaOriginal = Module._load;
Module._load = function (pedido, _padre, _esMain) {
  if (pedido.endsWith("_resend.js")) return mockResend;
  if (pedido.endsWith("_mp.js")) return mockMP;
  return cargaOriginal.apply(this, arguments);
};

global.fetch = async (url, opts) => {
  if (String(url).includes("/preapproval")) {
    return { ok: true, status: 200,
             json: async () => ({ init_point: "https://mp.test/suscribir", id: "sub_1" }) };
  }
  throw new Error("fetch inesperado en el test: " + url);
};

const API = path.join(__dirname, "..", "api");
const crearPreferencia = require(path.join(API, "create-preference.js"));
const crearSuscripcion = require(path.join(API, "create-subscription.js"));

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
// IP distinta por llamada: si no, el rate limiter de create-preference /
// create-subscription (10 pedidos/min por IP) tapa lo que cada test prueba.
const llamar = async (h, req) => {
  const res = resFalsa();
  await h({ method: "POST",
    headers: { host: "mvsqlnlp.com", "x-forwarded-for": "80.80.80." + Math.random() },
    body: {}, query: {}, ...req }, res);
  return res;
};

(async () => {
  console.log("\n== Aviso de intención de compra ==");

  await test("al generar la preferencia, avisa por mail al dueño", async () => {
    mails = [];
    const r = await llamar(crearPreferencia, {
      body: { plan: "implementacion", mode: "servicio", email: "cliente@test.com" },
    });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(mails.length, 1, "debe mandar exactamente un aviso");
    assert.strictEqual(mails[0].para, "vieraschiavi@gmail.com");
    assert.ok(mails[0].texto.includes("implementacion"));
    assert.ok(mails[0].texto.includes("cliente@test.com"));
    assert.ok(mails[0].texto.includes("2500"), "tiene que llevar el monto real del catálogo");
  });

  await test("al generar la suscripción, avisa por mail al dueño", async () => {
    mails = [];
    const r = await llamar(crearSuscripcion, { body: { plan: "profesional", email: "sub@test.com" } });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(mails.length, 1);
    assert.ok(mails[0].texto.includes("suscripcion"));
    assert.ok(mails[0].texto.includes("29"), "tiene que llevar el precio real del plan (US$29)");
  });

  await test("IDEMPOTENCIA: el mismo plan+email clickeado varias veces no manda un mail por click", async () => {
    mails = [];
    const datos = { plan: "empresa", mode: "servicio", email: "indeciso@test.com" };
    // Simula al mismo comprador tocando "Comprar" 3 veces seguidas.
    for (let i = 0; i < 3; i++) {
      await crearPreferencia({ method: "POST",
        headers: { host: "mvsqlnlp.com", "x-forwarded-for": "90.90.90.90" },
        query: {}, body: { ...datos, plan: "implementacion_express" } }, resFalsa());
    }
    assert.strictEqual(mails.length, 1,
      "3 clicks del mismo comprador tienen que generar 1 solo mail, no 3");
  });

  await test("un plan/email distinto SÍ genera un aviso nuevo (no es un candado global)", async () => {
    mails = [];
    await llamar(crearPreferencia, {
      body: { plan: "implementacion_express", mode: "servicio", email: "otro-cliente@test.com" },
    });
    assert.strictEqual(mails.length, 1);
  });

  await test("SI RESEND FALLA, EL COBRO SIGUE FUNCIONANDO (el checkout no puede depender del mail)", async () => {
    const rota = { enviarMail: async () => { throw new Error("Resend caído"); } };
    Module._load = function (pedido, _padre, _esMain) {
      if (pedido.endsWith("_resend.js")) return rota;
      if (pedido.endsWith("_mp.js")) return mockMP;
      return cargaOriginal.apply(this, arguments);
    };
    delete require.cache[require.resolve(path.join(API, "create-preference.js"))];
    delete require.cache[require.resolve(path.join(API, "_aviso-compra.js"))];
    const conFalla = require(path.join(API, "create-preference.js"));
    const r = await llamar(conFalla, {
      body: { plan: "implementacion", mode: "servicio", email: "resiliente@test.com" },
    });
    assert.strictEqual(r.statusCode, 200, "el checkout no puede romperse porque el aviso falló");
    assert.ok(r.body.init_point, "debe devolver igual el link de pago");
    // Restaura el mock sano para no afectar tests que corran después en este archivo.
    Module._load = function (pedido, _padre, _esMain) {
      if (pedido.endsWith("_resend.js")) return mockResend;
      if (pedido.endsWith("_mp.js")) return mockMP;
      return cargaOriginal.apply(this, arguments);
    };
    delete require.cache[require.resolve(path.join(API, "create-preference.js"))];
    delete require.cache[require.resolve(path.join(API, "_aviso-compra.js"))];
  });

  await test("un pedido inválido (email malo) NO genera aviso", async () => {
    mails = [];
    const r = await llamar(crearPreferencia, {
      body: { plan: "implementacion", mode: "servicio", email: "no-es-email" },
    });
    assert.strictEqual(r.statusCode, 400);
    assert.strictEqual(mails.length, 0, "un pedido rechazado no es intención de compra real");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
