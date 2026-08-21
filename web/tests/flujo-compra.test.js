/* © 2026 Martín Viera. Todos los derechos reservados. */

/**
 * Pruebas del flujo de compra completo: preferencia → pago → licencia → descarga.
 * Sin dependencias externas: mockea MercadoPago y corre con `node tests/flujo-compra.test.js`.
 *
 * Cubre los caminos que, si se rompen, hacen perder plata:
 *  - se cobra un plan que no existe / precio manipulado desde el cliente
 *  - se emite licencia sin que el pago esté aprobado (fraude)
 *  - se descarga el producto con una licencia inválida, vencida o de otro plan
 *  - el modo "créditos" no embebe la licencia en el zip
 */
const assert = require("assert");
const path = require("path");
const Module = require("module");

process.env.LICENSE_SECRET = "secreto-de-prueba-no-usar-en-produccion";
process.env.MP_ACCESS_TOKEN = "TEST-token";

// ── Mock de MercadoPago: no se llama a la red en los tests ──────────────
let pagoSimulado = { status: "approved", id: 123456, transaction_amount: 39 };
const mockMP = {
  client: () => ({}),
  Preference: class {
    async create({ body }) {
      mockMP.ultimaPreferencia = body;
      return { init_point: "https://mp.test/checkout/abc", id: "pref_1" };
    }
  },
  Payment: class {
    async get({ id }) {
      return { ...pagoSimulado, id: Number(id) };
    }
  },
};

const cargaOriginal = Module._load;
// Se usa `arguments` para reenviar la llamada original, así que los dos
// parámetros de más van con guion bajo: están por firma, no por uso.
Module._load = function (pedido, _padre, _esMain) {
  if (pedido.endsWith("_mp.js")) return mockMP;
  return cargaOriginal.apply(this, arguments);
};

const API = path.join(__dirname, "..", "api");
const crearPreferencia = require(path.join(API, "create-preference.js"));
const verificarYEmitir = require(path.join(API, "verify-and-issue.js"));
const descargar = require(path.join(API, "download.js"));
const descargarLicencia = require(path.join(API, "download-licencia.js"));
const descargarInstalador = require(path.join(API, "download-instalador.js"));
const { verifyLicense, CREDITS_BY_PLAN } = require(path.join(API, "_license.js"));
const { PRODUCTS } = require(path.join(API, "_products.js"));

// ── Utilidades de test ─────────────────────────────────────────────────
function resFalsa() {
  const r = { statusCode: null, body: null, headers: {} };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.send = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; return r; };
  r.end = (b) => { if (b) r.body = b; return r; };
  return r;
}
const llamar = async (handler, req) => {
  const res = resFalsa();
  await handler({ method: "POST", headers: { host: "mvsqlnlp.com" }, body: {}, query: {}, ...req }, res);
  return res;
};

let pasadas = 0, falladas = 0;
async function test(nombre, fn) {
  try {
    await fn();
    console.log(`  ✓ ${nombre}`);
    pasadas++;
  } catch (e) {
    console.log(`  ✗ ${nombre}\n      ${e.message}`);
    falladas++;
  }
}

(async () => {
  console.log("\n== 1. Creación de preferencia de pago ==");

  await test("cobra la implementación al precio del catálogo del servidor", async () => {
    const r = await llamar(crearPreferencia, {
      body: { plan: "implementacion", mode: "servicio", email: "cliente@test.com" },
    });
    assert.strictEqual(r.statusCode, 200);
    assert.ok(r.body.init_point, "debe devolver init_point");
    assert.strictEqual(mockMP.ultimaPreferencia.items[0].unit_price,
      PRODUCTS["implementacion:servicio"].price);
    assert.strictEqual(mockMP.ultimaPreferencia.items[0].unit_price, 2500);
  });

  await test("ignora un precio inyectado desde el cliente", async () => {
    await llamar(crearPreferencia, {
      body: { plan: "implementacion", mode: "servicio", email: "a@b.com",
              price: 1, unit_price: 1 },
    });
    assert.strictEqual(mockMP.ultimaPreferencia.items[0].unit_price, 2500,
      "el precio debe venir del catálogo del servidor, no del cliente");
  });

  await test("NO deja cobrar una suscripción como pago único", async () => {
    const r = await llamar(crearPreferencia, {
      body: { plan: "profesional", mode: "suscripcion", email: "a@b.com" },
    });
    assert.strictEqual(r.statusCode, 400,
      "cobrar una suscripción una sola vez es el bug que arruina el negocio");
  });

  await test("rechaza plan inexistente", async () => {
    const r = await llamar(crearPreferencia, {
      body: { plan: "gratis-total", mode: "own_ai", email: "a@b.com" },
    });
    assert.strictEqual(r.statusCode, 400);
  });

  await test("rechaza email inválido", async () => {
    const r = await llamar(crearPreferencia, {
      body: { plan: "personal", mode: "credits", email: "no-es-email" },
    });
    assert.strictEqual(r.statusCode, 400);
  });

  await test("el external_reference permite reconstruir la compra", async () => {
    // Se usa un producto que HOY se vende. Antes esto compraba
    // "personal:credits", y los paquetes de créditos se dejaron de vender:
    // el catálogo ya no los tiene, así que create-preference los rechaza
    // — que es exactamente lo que tiene que pasar.
    await llamar(crearPreferencia, {
      body: { plan: "implementacion_express", mode: "servicio", email: "x@y.com" },
    });
    assert.strictEqual(mockMP.ultimaPreferencia.external_reference,
      "implementacion_express:servicio:x@y.com");
  });

  await test("un paquete de créditos YA NO SE PUEDE COMPRAR", async () => {
    // El modelo pasó a ser que cada cliente ponga su propia API key. Si el
    // catálogo volviera a aceptarlos, se estaría vendiendo algo cuyo costo
    // de IA pagamos nosotros y que la app ya no ofrece.
    const r = await llamar(crearPreferencia, {
      body: { plan: "personal", mode: "credits", email: "x@y.com" },
    });
    assert.strictEqual(r.statusCode, 400, "el catálogo todavía vende créditos");
  });

  console.log("\n== 2. Verificación de pago y emisión de licencia ==");

  let licenciaValida = null;

  // El modo "credits" se sigue verificando a propósito aunque ya no se
  // venda: quien compró un paquete antes tiene que poder seguir usándolo,
  // y esa rama de _license.js y download.js sigue viva por eso.
  await test("emite licencia solo si MercadoPago dice approved", async () => {
    pagoSimulado = { status: "approved", id: 555, transaction_amount: 39,
                     external_reference: "profesional:credits:c@t.com" };
    const r = await llamar(verificarYEmitir, {
      method: "GET", query: { payment_id: 555 },
    });
    assert.strictEqual(r.statusCode, 200, `esperaba 200, vino ${r.statusCode}: ${JSON.stringify(r.body)}`);
    assert.ok(r.body.token, "debe devolver la licencia");
    licenciaValida = r.body.token;
  });

  await test("NO emite licencia si el pago está pendiente", async () => {
    pagoSimulado = { status: "pending", id: 556, external_reference: "empresa:credits:c@t.com" };
    const r = await llamar(verificarYEmitir, { method: "GET", query: { payment_id: 556 } });
    assert.notStrictEqual(r.statusCode, 200, "un pago pendiente no puede habilitar la descarga");
  });

  await test("NO emite licencia si el pago fue rechazado", async () => {
    pagoSimulado = { status: "rejected", id: 557, external_reference: "empresa:credits:c@t.com" };
    const r = await llamar(verificarYEmitir, { method: "GET", query: { payment_id: 557 } });
    assert.notStrictEqual(r.statusCode, 200, "un pago rechazado no puede habilitar la descarga");
  });

  await test("la licencia lleva los créditos del plan comprado", async () => {
    pagoSimulado = { status: "approved", id: 558, external_reference: "empresa:credits:e@t.com" };
    const r = await llamar(verificarYEmitir, { method: "GET", query: { payment_id: 558 } });
    const datos = verifyLicense(r.body.token);
    assert.strictEqual(datos.credits, CREDITS_BY_PLAN.empresa);
    assert.strictEqual(datos.email, "e@t.com");
  });

  await test("un servicio no otorga créditos de IA nuestra", async () => {
    pagoSimulado = { status: "approved", id: 559, external_reference: "implementacion:servicio:o@t.com" };
    const r = await llamar(verificarYEmitir, { method: "GET", query: { payment_id: 559 } });
    assert.strictEqual(verifyLicense(r.body.token).credits, 0,
      "una implementación no otorga créditos de IA nuestra");
  });

  await test("rechaza pago con external_reference corrupto", async () => {
    pagoSimulado = { status: "approved", id: 560, external_reference: "basura" };
    const r = await llamar(verificarYEmitir, { method: "GET", query: { payment_id: 560 } });
    assert.strictEqual(r.statusCode, 400);
  });

  console.log("\n== 3. Descarga protegida ==");

  await test("rechaza descarga sin licencia", async () => {
    const r = await llamar(descargar, { method: "GET", query: {} });
    assert.notStrictEqual(r.statusCode, 200);
  });

  await test("rechaza licencia falsificada", async () => {
    const r = await llamar(descargar, {
      method: "GET", query: { token: "esto.no.es.un.jwt" },
    });
    assert.notStrictEqual(r.statusCode, 200);
  });

  await test("rechaza licencia firmada con otro secreto", async () => {
    const jwt = require("jsonwebtoken");
    const falsa = jwt.sign({ email: "h@x.com", plan: "empresa", mode: "credits", credits: 2000 },
      "secreto-del-atacante", { expiresIn: "365d" });
    const r = await llamar(descargar, { method: "GET", query: { token: falsa } });
    assert.notStrictEqual(r.statusCode, 200, "una licencia firmada por un tercero no puede pasar");
  });

  await test("acepta la licencia legítima y entrega el zip", async () => {
    const r = await llamar(descargar, { method: "GET", query: { token: licenciaValida } });
    assert.strictEqual(r.statusCode, 200, `esperaba 200, vino ${r.statusCode}: ${JSON.stringify(r.body).slice(0, 200)}`);
    assert.ok(/zip/i.test(r.headers["Content-Type"] || r.headers["content-type"] || ""),
      "debe entregar un archivo zip");
  });

  console.log("\n== 4. Descarga de la licencia suelta (para el programa de escritorio) ==");

  // El programa de escritorio (Electron) no lee el .zip: su pantalla "Ya
  // tengo una licencia" pide un archivo .json suelto (ver
  // desktop/electron/main.cjs). Este endpoint es la única forma
  // descubrible de conseguir ese archivo — antes había que bajar el zip
  // entero y encontrarlo a mano adentro de nl2sql_rag/. Mismo gate de
  // seguridad que /api/download: se prueba la misma superficie.

  await test("rechaza sin licencia", async () => {
    const r = await llamar(descargarLicencia, { method: "GET", query: {} });
    assert.notStrictEqual(r.statusCode, 200);
  });

  await test("rechaza licencia falsificada", async () => {
    const r = await llamar(descargarLicencia, {
      method: "GET", query: { token: "esto.no.es.un.jwt" },
    });
    assert.notStrictEqual(r.statusCode, 200);
  });

  await test("rechaza licencia firmada con otro secreto", async () => {
    const jwt = require("jsonwebtoken");
    const falsa = jwt.sign({ email: "h@x.com", plan: "empresa", mode: "credits", credits: 2000 },
      "secreto-del-atacante", { expiresIn: "365d" });
    const r = await llamar(descargarLicencia, { method: "GET", query: { token: falsa } });
    assert.notStrictEqual(r.statusCode, 200, "una licencia firmada por un tercero no puede pasar");
  });

  await test("acepta la licencia legítima y entrega SOLO el .json, sin el zip alrededor", async () => {
    const r = await llamar(descargarLicencia, { method: "GET", query: { token: licenciaValida } });
    assert.strictEqual(r.statusCode, 200, `esperaba 200, vino ${r.statusCode}: ${JSON.stringify(r.body).slice(0, 200)}`);
    const tipo = r.headers["Content-Type"] || r.headers["content-type"] || "";
    assert.ok(/json/i.test(tipo), `debe entregar JSON, entregó "${tipo}"`);
    assert.ok(/licencia_mvsql\.json/.test(r.headers["Content-Disposition"] || ""),
      "el nombre del archivo debe ser licencia_mvsql.json, igual que el que va adentro del zip");

    // Tiene que ser el MISMO contenido que download.js embebe en el zip:
    // dos endpoints armando el archivo de formas distintas es justo el bug
    // que _licencia-archivo.js existe para evitar (ver su comentario).
    const licenciaJson = JSON.parse(r.body);
    assert.strictEqual(licenciaJson.token, licenciaValida);
    assert.ok(licenciaJson.vence, "debe traer fecha de vencimiento");
    assert.strictEqual(licenciaJson.modo, "credits");
  });

  console.log("\n== 5. Descarga del instalador completo (.exe) — antes era un link público ==");

  // MV-SQL-NLP-Setup.exe no tenía NINGÚN endpoint que lo entregara gateado
  // (a diferencia del zip): era un link público sin chequeo. Al sacar la
  // descarga pública del trial, este es el único camino que le queda al
  // cliente que pagó y quiere justo este formato de instalador.

  await test("rechaza sin licencia", async () => {
    const r = await llamar(descargarInstalador, { method: "GET", query: {} });
    assert.notStrictEqual(r.statusCode, 200);
  });

  await test("rechaza licencia falsificada", async () => {
    const r = await llamar(descargarInstalador, {
      method: "GET", query: { token: "esto.no.es.un.jwt" },
    });
    assert.notStrictEqual(r.statusCode, 200);
  });

  await test("rechaza licencia firmada con otro secreto", async () => {
    const jwt = require("jsonwebtoken");
    const falsa = jwt.sign({ email: "h@x.com", plan: "empresa", mode: "credits", credits: 2000 },
      "secreto-del-atacante", { expiresIn: "365d" });
    const r = await llamar(descargarInstalador, { method: "GET", query: { token: falsa } });
    assert.notStrictEqual(r.statusCode, 200, "una licencia firmada por un tercero no puede pasar");
  });

  await test("acepta la licencia legítima y entrega el .exe", async () => {
    const r = await llamar(descargarInstalador, { method: "GET", query: { token: licenciaValida } });
    assert.strictEqual(r.statusCode, 200, `esperaba 200, vino ${r.statusCode}: ${JSON.stringify(r.body).slice(0, 200)}`);
    assert.ok(/octet-stream/i.test(r.headers["Content-Type"] || r.headers["content-type"] || ""));
    assert.ok(/MV-SQL-NLP-Setup\.exe/.test(r.headers["Content-Disposition"] || ""));
  });

  console.log(`\n${"=".repeat(52)}`);
  console.log(`  ${pasadas} pasadas · ${falladas} falladas`);
  console.log("=".repeat(52));
  process.exit(falladas ? 1 : 0);
})();
