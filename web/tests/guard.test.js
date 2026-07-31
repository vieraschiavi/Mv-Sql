/** Validación de entrada y rate limiting (web/api/_guard.js).
 *
 * El regex de email que había antes (/^\S+@\S+\.\S+$/) aceptaba payloads
 * HTML, que terminaban en external_reference y de ahí en el panel del
 * dueño. Y ningún endpoint tenía freno de pedidos, así que
 * /api/verify-and-issue se podía barrer por fuerza bruta.
 */
const assert = require("assert");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const { emailValido, permitido, ipDe, limitar } = require(
  path.join(__dirname, "..", "api", "_guard.js"));

function resFalsa() {
  const r = { statusCode: null, body: null, headers: {} };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.send = (b) => { r.body = b; return r; };
  r.setHeader = (k, v) => { r.headers[k] = v; };
  return r;
}

(async () => {
  console.log("\n== Validación de email ==");

  await test("acepta direcciones normales", () => {
    for (const e of ["ana@empresa.com", "juan.perez+mv@sub.dominio.com.uy",
                     "a_b-c%d@x.io"]) {
      assert.ok(emailValido(e), `debería aceptar ${e}`);
    }
  });

  await test("rechaza el payload XSS que el regex viejo dejaba pasar", () => {
    // Sin espacios => /^\S+@\S+\.\S+$/ lo daba por válido.
    const ataque = "<svg/onload=alert(1)>@a.co";
    assert.ok(/^\S+@\S+\.\S+$/.test(ataque), "premisa: el regex viejo lo aceptaba");
    assert.strictEqual(emailValido(ataque), false, "el nuevo debe rechazarlo");
  });

  await test("rechaza comillas, < > y barras", () => {
    for (const e of ['"><img src=x onerror=alert(1)>@a.co', "a'b@a.co",
                     "a/b@a.co", "a\\b@a.co", 'a"b@a.co']) {
      assert.strictEqual(emailValido(e), false, `debería rechazar ${e}`);
    }
  });

  await test("rechaza vacío, no-string y desmesurados", () => {
    assert.strictEqual(emailValido(""), false);
    assert.strictEqual(emailValido(null), false);
    assert.strictEqual(emailValido(undefined), false);
    assert.strictEqual(emailValido({}), false);
    assert.strictEqual(emailValido("a".repeat(250) + "@x.com"), false);
  });

  await test("rechaza formas incompletas", () => {
    for (const e of ["sin-arroba.com", "a@sin-tld", "@a.com", "a@.com"]) {
      assert.strictEqual(emailValido(e), false, `debería rechazar ${e}`);
    }
  });

  console.log("\n== Rate limiting ==");

  await test("deja pasar hasta el máximo y frena el siguiente", () => {
    const clave = "prueba-" + Math.random();
    for (let i = 0; i < 5; i++) {
      assert.strictEqual(permitido(clave, 5, 60000), true, `pedido ${i + 1}`);
    }
    assert.strictEqual(permitido(clave, 5, 60000), false, "el 6º debe frenarse");
  });

  await test("cada clave tiene su propia cuenta", () => {
    const a = "a-" + Math.random(), b = "b-" + Math.random();
    assert.strictEqual(permitido(a, 1, 60000), true);
    assert.strictEqual(permitido(a, 1, 60000), false, "a agotado");
    assert.strictEqual(permitido(b, 1, 60000), true, "b no debe verse afectado");
  });

  await test("la ventana se renueva al vencer", async () => {
    const clave = "ventana-" + Math.random();
    assert.strictEqual(permitido(clave, 1, 40), true);
    assert.strictEqual(permitido(clave, 1, 40), false);
    await new Promise((r) => setTimeout(r, 60));
    assert.strictEqual(permitido(clave, 1, 40), true, "tras vencer debe permitir");
  });

  await test("limitar() contesta 429 con Retry-After", () => {
    const req = { headers: { "x-forwarded-for": "9.9.9.9" } };
    const nombre = "t429-" + Math.random();
    assert.strictEqual(limitar(req, resFalsa(), { max: 1, ventanaMs: 60000, nombre }), true);
    const res = resFalsa();
    assert.strictEqual(limitar(req, res, { max: 1, ventanaMs: 60000, nombre }), false);
    assert.strictEqual(res.statusCode, 429);
    assert.strictEqual(res.headers["Retry-After"], 60);
  });

  await test("ipDe() no revienta con un req incompleto", () => {
    // Un req sin headers rompía el endpoint entero: los tests del panel
    // del dueño lo detectaron al agregar el rate limiting.
    assert.strictEqual(ipDe({}), "desconocida");
    assert.strictEqual(ipDe(undefined), "desconocida");
    assert.strictEqual(ipDe({ headers: {} }), "desconocida");
    assert.strictEqual(ipDe({ headers: { "x-forwarded-for": "1.2.3.4, 5.6.7.8" } }), "1.2.3.4");
    assert.strictEqual(ipDe({ socket: { remoteAddress: "7.7.7.7" } }), "7.7.7.7");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
