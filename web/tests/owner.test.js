/** Pruebas del panel del dueño: seguridad del token + agregación de ventas. */
const assert = require("assert");
const path = require("path");

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
const llamar = async (h, query) => { const res = resFalsa(); await h({ query }, res); return res; };

// Ventas simuladas de MercadoPago
const hoy = new Date().toISOString();
const PAGOS = [
  { status: "approved", transaction_amount: 39, date_approved: hoy,
    external_reference: "profesional:own_ai:ana@empresa.com", payment_method_id: "visa" },
  { status: "approved", transaction_amount: 99, date_approved: hoy,
    external_reference: "empresa:own_ai:cto@banco.com", payment_method_id: "master" },
  { status: "approved", transaction_amount: 35, date_approved: hoy,
    external_reference: "profesional:credits:ana@empresa.com", payment_method_id: "visa" },
  { status: "rejected", transaction_amount: 39, date_created: hoy,
    external_reference: "profesional:own_ai:x@y.com" },
  { status: "pending", transaction_amount: 19, date_created: hoy,
    external_reference: "personal:own_ai:z@y.com" },
];
global.fetch = async () => ({ ok: true, status: 200, json: async () => ({ results: PAGOS }) });

const ownerStats = require(path.join(__dirname, "..", "api", "owner-stats.js"));

(async () => {
  console.log("\n== Panel del dueño ==");

  await test("queda cerrado si no hay OWNER_TOKEN configurado", async () => {
    delete process.env.OWNER_TOKEN;
    const r = await llamar(ownerStats, { token: "loquesea" });
    assert.strictEqual(r.statusCode, 503, "sin configurar debe estar cerrado, no abierto");
  });

  process.env.OWNER_TOKEN = "token-secreto-del-duenio";
  process.env.MP_ACCESS_TOKEN = "TEST-mp";

  await test("rechaza token vacío", async () => {
    assert.strictEqual((await llamar(ownerStats, {})).statusCode, 401);
  });

  await test("rechaza token incorrecto", async () => {
    assert.strictEqual((await llamar(ownerStats, { token: "adivinado" })).statusCode, 401);
  });

  await test("rechaza token con prefijo correcto pero incompleto", async () => {
    assert.strictEqual((await llamar(ownerStats, { token: "token-secreto" })).statusCode, 401);
  });

  let datos;
  await test("acepta el token correcto", async () => {
    const r = await llamar(ownerStats, { token: "token-secreto-del-duenio" });
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    datos = r.body;
  });

  await test("suma solo los pagos aprobados", async () => {
    assert.strictEqual(datos.resumen.ventas_totales, 3, "3 aprobados de 5 pagos");
    assert.strictEqual(datos.resumen.ingreso_total_usd, 39 + 99 + 35);
  });

  await test("cuenta rechazados y pendientes por separado", async () => {
    assert.strictEqual(datos.resumen.pagos_rechazados, 1);
    assert.strictEqual(datos.resumen.pagos_pendientes, 1);
    assert.strictEqual(datos.resumen.tasa_aprobacion, 60, "3 de 5 = 60%");
  });

  await test("no cuenta dos veces al mismo cliente", async () => {
    assert.strictEqual(datos.resumen.clientes_unicos, 2,
      "ana compró 2 veces: es 1 cliente");
  });

  await test("desglosa por producto con el título del catálogo", async () => {
    const emp = datos.por_producto.find((p) => p.clave === "empresa:own_ai");
    assert.ok(emp, "debe aparecer el plan empresa");
    assert.strictEqual(emp.usd, 99);
    assert.ok(/Empresa/.test(emp.producto), "usa el título del catálogo");
  });

  await test("calcula el ticket promedio", async () => {
    assert.strictEqual(datos.resumen.ticket_promedio_usd, Math.round((39 + 99 + 35) / 3));
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
