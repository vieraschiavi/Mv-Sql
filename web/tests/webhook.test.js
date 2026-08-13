/* © 2026 Martín Viera. Todos los derechos reservados. */

/** /api/webhook — rate limiting (web/api/webhook.js).
 *
 * Todos los endpoints de pago tenían freno de pedidos salvo este: al no
 * emitir nada por sí mismo (solo loguea y reconcilia) parecía "menos
 * obvio", pero es público, no pide ninguna prueba de que quien llama es
 * MercadoPago, y cada pedido con "data.id" dispara una llamada saliente
 * real a la API de MercadoPago — barrerlo por fuerza bruta cuesta cupo y
 * dinero igual que barrear cualquier otro endpoint.
 */
const assert = require("assert");
const path = require("path");

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
  r.setHeader = (k, v) => { r.headers[k] = v; };
  return r;
}

// Sin MP_ACCESS_TOKEN, _mp.js tira al construir el cliente; webhook.js lo
// atrapa y responde 200 igual (para que MercadoPago no reintente en loop).
// No hace falta mockear la red para probar el freno de pedidos.
delete process.env.MP_ACCESS_TOKEN;
const webhook = require(path.join(__dirname, "..", "api", "webhook.js"));

(async () => {
  console.log("\n== /api/webhook: rate limiting ==");

  await test("pedidos normales responden 200", async () => {
    const req = { headers: { "x-forwarded-for": "50.50.50." + Math.random() }, query: {}, body: {} };
    const res = resFalsa();
    await webhook(req, res);
    assert.strictEqual(res.statusCode, 200);
  });

  await test("pasado el máximo por minuto, frena con 429 y no llama a MercadoPago", async () => {
    const ip = "60.60.60." + Math.random();
    const req = () => ({ headers: { "x-forwarded-for": ip }, query: {}, body: {} });
    let ultimo;
    for (let i = 0; i < 61; i++) {
      ultimo = resFalsa();
      await webhook(req(), ultimo);
    }
    assert.strictEqual(ultimo.statusCode, 429, "el pedido 61 en el mismo minuto debe frenarse");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
