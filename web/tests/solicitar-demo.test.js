/* © 2026 Martín Viera. Todos los derechos reservados. */

/** /api/solicitar-demo — pedir demo reemplaza la descarga pública del
 * trial. Se prueba: valida los campos, frena el abuso, y cuando todo está
 * bien manda el mail (mockeado — sin red real) con lo que la persona
 * completó, no con lo que ella podría haber mandado en un campo distinto.
 */
const assert = require("assert");
const path = require("path");
const Module = require("module");

let ultimoMail = null;
const mockResend = {
  enviarMail: async (datos) => { ultimoMail = datos; return { id: "mail_test" }; },
};

const cargaOriginal = Module._load;
Module._load = function (pedido, _padre, _esMain) {
  if (pedido.endsWith("_resend.js")) return mockResend;
  return cargaOriginal.apply(this, arguments);
};

const API = path.join(__dirname, "..", "api");
const solicitarDemo = require(path.join(API, "solicitar-demo.js"));

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

function resFalsa() {
  const r = { statusCode: null, body: null, headers: {} };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.send = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; return r; };
  return r;
}
const llamar = async (req) => {
  const res = resFalsa();
  ultimoMail = null;
  // IP distinta por llamada: si no, los propios tests agotan entre ellos
  // la cuota de 5/min de este endpoint y el 429 tapa lo que cada test
  // quiere probar en realidad.
  await solicitarDemo({ method: "POST",
    headers: { host: "mvsqlnlp.com", "x-forwarded-for": "50.50.50." + Math.random() },
    query: {}, body: {}, ...req }, res);
  return res;
};

const DATOS_OK = { nombre: "Ana Pérez", pais: "Uruguay", empresa: "Acme SA", email: "ana@acme.com" };

(async () => {
  console.log("\n== /api/solicitar-demo ==");

  await test("rechaza otro método que no sea POST", async () => {
    const res = resFalsa();
    await solicitarDemo({ method: "GET" }, res);
    assert.strictEqual(res.statusCode, 405);
  });

  await test("con todos los campos completos, manda el mail y responde 200", async () => {
    const r = await llamar({ body: DATOS_OK });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.ok(ultimoMail, "no se llamó a enviarMail");
    assert.strictEqual(ultimoMail.para, "vieraschiavi@gmail.com");
    assert.strictEqual(ultimoMail.replyTo, DATOS_OK.email);
  });

  await test("EL MAIL LLEVA LO QUE LA PERSONA COMPLETÓ, cada campo en su lugar", async () => {
    await llamar({ body: DATOS_OK });
    assert.ok(ultimoMail.texto.includes("Ana Pérez"));
    assert.ok(ultimoMail.texto.includes("Uruguay"));
    assert.ok(ultimoMail.texto.includes("Acme SA"));
    assert.ok(ultimoMail.asunto.includes("Acme SA"), "el asunto identifica la empresa que pidió la demo");
  });

  for (const campo of ["nombre", "pais", "empresa"]) {
    await test(`rechaza sin "${campo}"`, async () => {
      const datos = { ...DATOS_OK, [campo]: "" };
      const r = await llamar({ body: datos });
      assert.strictEqual(r.statusCode, 400);
      assert.strictEqual(ultimoMail, null, "no debe mandar mail si falta un campo");
    });
  }

  await test("rechaza email inválido", async () => {
    const r = await llamar({ body: { ...DATOS_OK, email: "no-es-email" } });
    assert.strictEqual(r.statusCode, 400);
    assert.strictEqual(ultimoMail, null);
  });

  await test("HTML EN UN CAMPO no pasa: se corta antes de llegar al mail", async () => {
    const r = await llamar({ body: { ...DATOS_OK, empresa: "<img src=x onerror=alert(1)>" } });
    assert.strictEqual(r.statusCode, 400);
    assert.strictEqual(ultimoMail, null);
  });

  await test("un campo pasado de largo se rechaza (no un mail gigante)", async () => {
    const r = await llamar({ body: { ...DATOS_OK, nombre: "a".repeat(500) } });
    assert.strictEqual(r.statusCode, 400);
  });

  await test("frena el abuso: después del máximo por minuto, 429", async () => {
    const req = { headers: { "x-forwarded-for": "60.60.60." + Math.random(), host: "mvsqlnlp.com" },
      method: "POST", query: {}, body: DATOS_OK };
    let ultimo;
    for (let i = 0; i < 6; i++) {
      const res = resFalsa();
      await solicitarDemo(req, res);
      ultimo = res;
    }
    assert.strictEqual(ultimo.statusCode, 429);
  });

  await test("si Resend falla, no revienta: 500 con mensaje accionable, no 200", async () => {
    const rota = { enviarMail: async () => { throw new Error("Resend caído"); } };
    Module._load = function (pedido, _padre, _esMain) {
      if (pedido.endsWith("_resend.js")) return rota;
      return cargaOriginal.apply(this, arguments);
    };
    delete require.cache[require.resolve(path.join(API, "solicitar-demo.js"))];
    const conFalla = require(path.join(API, "solicitar-demo.js"));
    const res = resFalsa();
    await conFalla({ method: "POST", headers: { host: "mvsqlnlp.com", "x-forwarded-for": "70.70.70." + Math.random() },
      query: {}, body: DATOS_OK }, res);
    assert.strictEqual(res.statusCode, 500);
    assert.ok(/vieraschiavi@gmail.com/.test(res.body.error),
      "si falla el envío automático, el mensaje tiene que decir cómo escribir directo");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
