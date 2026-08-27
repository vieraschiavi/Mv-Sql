/* © 2026 Martín Viera. Todos los derechos reservados. */

/** /api/estado — ¿el sistema puede cobrar y entregar ahora mismo?
 *
 * Nace de un hueco real encontrado auditando producción: desde afuera no
 * hay forma de saber si falta una clave. Si LICENSE_SECRET no está
 * configurada, /api/download responde 401 "tu enlace no es válido" —
 * exactamente igual que ante un token falsificado, porque el catch de
 * verifyLicense no distingue una cosa de la otra. Como seguridad está
 * bien (no le cuenta a un atacante qué falta), pero deja al dueño ciego:
 * el modo de falla es un cliente que paga, vuelve a /gracias y no recibe
 * la licencia, sin ninguna señal previa de que iba a pasar.
 *
 * Lo que se prueba acá, en orden de importancia:
 *  - que NUNCA devuelva el valor de una variable, solo si está o no
 *  - que esté cerrado a quien no tenga el OWNER_TOKEN
 *  - que "listo_para_vender" mire las críticas (cobrar y entregar) y no
 *    se ponga en false por una variable opcional
 */
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

const estado = require(path.join(__dirname, "..", "api", "estado.js"));

// IP distinta por llamada: si no, los propios tests agotan la cuota por
// minuto del endpoint y el 429 tapa lo que cada caso quiere probar.
const llamar = async (query) => {
  const res = resFalsa();
  await estado({ method: "GET", query,
    headers: { host: "mvsqlnlp.com", "x-forwarded-for": "40.40.40." + Math.random() } }, res);
  return res;
};

const SECRETO_OWNER = "token-de-prueba-del-duenio";

// Deja el entorno con exactamente las variables que se pidan.
function entorno(puestas) {
  for (const v of ["MP_ACCESS_TOKEN", "LICENSE_SECRET", "OWNER_TOKEN",
                   "RESEND_API_KEY", "ANTHROPIC_API_KEY", "KV_REST_API_URL"]) {
    delete process.env[v];
  }
  for (const [k, val] of Object.entries(puestas)) process.env[k] = val;
}

(async () => {
  console.log("\n== /api/estado: ¿se puede cobrar y entregar? ==");

  await test("SIN OWNER_TOKEN queda cerrado, pero dice qué falta para abrirlo", async () => {
    entorno({});
    const r = await llamar({ token: "lo-que-sea" });
    assert.strictEqual(r.statusCode, 503);
    assert.match(r.body.error, /OWNER_TOKEN/,
      "tiene que nombrar la variable que falta, si no es imposible destrabarlo");
    assert.strictEqual(r.body.listo_para_vender, false);
  });

  await test("rechaza un token incorrecto", async () => {
    entorno({ OWNER_TOKEN: SECRETO_OWNER });
    const r = await llamar({ token: "no-es-el-token" });
    assert.strictEqual(r.statusCode, 401);
  });

  await test("rechaza sin token", async () => {
    entorno({ OWNER_TOKEN: SECRETO_OWNER });
    const r = await llamar({});
    assert.strictEqual(r.statusCode, 401);
  });

  await test("NUNCA DEVUELVE EL VALOR DE UNA VARIABLE, solo si está puesta", async () => {
    // Lo más importante del archivo: este endpoint existe para reportar
    // configuración, y un descuido lo convierte en una fuga de secretos.
    const secretos = {
      OWNER_TOKEN: SECRETO_OWNER,
      MP_ACCESS_TOKEN: "APP_USR-secreto-de-mercadopago-123",
      LICENSE_SECRET: "secreto-de-firma-de-licencias-456",
      RESEND_API_KEY: "re_secreto_de_resend_789",
    };
    entorno(secretos);
    const r = await llamar({ token: SECRETO_OWNER });
    assert.strictEqual(r.statusCode, 200);
    const texto = JSON.stringify(r.body);
    for (const [nombre, valor] of Object.entries(secretos)) {
      assert.ok(!texto.includes(valor),
        `¡FUGA! el valor de ${nombre} aparece en la respuesta`);
    }
    // y sí tiene que decir que están configuradas
    const porNombre = Object.fromEntries(r.body.variables.map((v) => [v.nombre, v]));
    assert.strictEqual(porNombre.MP_ACCESS_TOKEN.configurada, true);
    assert.strictEqual(porNombre.LICENSE_SECRET.configurada, true);
  });

  await test("CON LAS CRÍTICAS PUESTAS dice que se puede vender", async () => {
    entorno({ OWNER_TOKEN: SECRETO_OWNER, MP_ACCESS_TOKEN: "mp", LICENSE_SECRET: "lic" });
    const r = await llamar({ token: SECRETO_OWNER });
    assert.strictEqual(r.body.listo_para_vender, true,
      "con MP_ACCESS_TOKEN y LICENSE_SECRET se puede cobrar y entregar");
    assert.deepStrictEqual(r.body.faltan_criticas, []);
  });

  await test("SIN LICENSE_SECRET dice que NO se puede vender (el que paga no descarga)", async () => {
    entorno({ OWNER_TOKEN: SECRETO_OWNER, MP_ACCESS_TOKEN: "mp" });
    const r = await llamar({ token: SECRETO_OWNER });
    assert.strictEqual(r.body.listo_para_vender, false);
    assert.ok(r.body.faltan_criticas.includes("LICENSE_SECRET"));
    assert.match(r.body.resumen, /NO se puede vender/);
  });

  await test("SIN MP_ACCESS_TOKEN dice que NO se puede vender (nadie puede pagar)", async () => {
    entorno({ OWNER_TOKEN: SECRETO_OWNER, LICENSE_SECRET: "lic" });
    const r = await llamar({ token: SECRETO_OWNER });
    assert.strictEqual(r.body.listo_para_vender, false);
    assert.ok(r.body.faltan_criticas.includes("MP_ACCESS_TOKEN"));
  });

  await test("una variable OPCIONAL faltante NO bloquea la venta", async () => {
    // RESEND_API_KEY solo manda avisos: si tumbara "listo_para_vender",
    // el chequeo mentiría sobre lo único que de verdad importa.
    entorno({ OWNER_TOKEN: SECRETO_OWNER, MP_ACCESS_TOKEN: "mp", LICENSE_SECRET: "lic" });
    const r = await llamar({ token: SECRETO_OWNER });
    const resend = r.body.variables.find((v) => v.nombre === "RESEND_API_KEY");
    assert.strictEqual(resend.configurada, false);
    assert.strictEqual(resend.critica, false);
    assert.strictEqual(r.body.listo_para_vender, true);
  });

  await test("cada variable dice para qué sirve y dónde se carga", async () => {
    // Sin esto el chequeo dice "falta X" y el dueño igual no sabe qué hacer.
    entorno({ OWNER_TOKEN: SECRETO_OWNER });
    const r = await llamar({ token: SECRETO_OWNER });
    for (const v of r.body.variables) {
      assert.ok(v.para && v.para.length > 10, `${v.nombre} no explica para qué sirve`);
      assert.ok(v.donde && v.donde.length > 10, `${v.nombre} no dice dónde se carga`);
    }
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
