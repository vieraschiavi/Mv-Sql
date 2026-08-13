/* © 2026 Martín Viera. Todos los derechos reservados. */

/** La app PIDE la licencia nueva sola mientras el cliente siga pagando.
 *
 * El endpoint que renueva (web/api/renovar-licencia.js) existía desde
 * antes y no lo llamaba nadie: la mitad del servidor estaba hecha y la
 * del cliente no, así que la función completa no existía. Una suscripción
 * cobra todos los meses y la licencia se emitía una sola vez; en cuanto
 * la vigencia se acorte al ciclo de cobro —que es a donde tiene que ir—
 * el cliente que SÍ paga se queda afuera todos los meses si nadie pide
 * la licencia nueva por él.
 *
 * Lo que se fija acá es sobre todo lo que NO tiene que pasar. La regla es
 * que renovar no puede dejar al cliente peor que antes: sin red, con el
 * servidor caído, con una respuesta rota o con una suscripción cancelada,
 * la licencia que ya tenía queda intacta y la app abre igual.
 *
 * Y el caso que se paga caro y no se ve venir: que la licencia nueva
 * llegue SIN `vence`. Se escribiría encima de la buena, `vigente()` daría
 * false al instante, y el cliente vería "comprá tu licencia" justo
 * después de una renovación exitosa. Por eso el último test hace el
 * viaje entero: lo que devuelve el endpoint de verdad, guardado por el
 * cliente de verdad.
 */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

process.env.LICENSE_SECRET = "secreto-de-prueba";
process.env.MP_ACCESS_TOKEN = "TEST-mp";

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const licencia = require(path.join(RAIZ, "desktop", "electron", "services", "licencia.cjs"));

const DIA = 86400000;
const enDias = (n) => new Date(Date.now() + n * DIA).toISOString();

/** Un userData limpio con una licencia paga adentro. */
function conLicencia(extra = {}) {
  const datos = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-renov-"));
  const lic = {
    producto: "MV SQL NLP",
    email: "cliente@empresa.com",
    plan: "profesional",
    modo: "own_ai",
    token: "el-token-del-cliente",
    vence: enDias(2),
    ...extra,
  };
  fs.writeFileSync(path.join(datos, "licencia_mvsql.json"), JSON.stringify(lic, null, 2));
  // `recursos` apunta a un directorio vacío: sin licencia de propietario.
  return { dirs: { datos, recursos: datos }, archivo: path.join(datos, "licencia_mvsql.json"), lic };
}
const leer = (a) => JSON.parse(fs.readFileSync(a, "utf8"));

/** fetch falso que anota si lo llamaron y con qué. */
function fetchFalso(respuesta) {
  const f = async (url) => {
    f.llamadas.push(url);
    if (respuesta instanceof Error) throw respuesta;
    return respuesta;
  };
  f.llamadas = [];
  return f;
}
const resp = (status, cuerpo) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => cuerpo,
});

(async () => {
  console.log("\n== La app renueva la licencia sola ==");

  await test("CON LA LICENCIA POR VENCER Y LA SUSCRIPCIÓN PAGA, la renueva", async () => {
    const { dirs, archivo } = conLicencia();
    const nueva = { producto: "MV SQL NLP", modo: "own_ai", token: "token-nuevo",
                    vence: enDias(35), email: "cliente@empresa.com", plan: "profesional" };
    const f = fetchFalso(resp(200, { token: "token-nuevo", licencia: nueva }));

    const r = await licencia.renovarSiCorresponde(dirs, { fetch: f });
    assert.strictEqual(r.estado, "renovada", `no renovó: ${JSON.stringify(r)}`);
    assert.strictEqual(leer(archivo).token, "token-nuevo",
      "dijo que renovó pero el archivo quedó con la licencia vieja");
    assert.ok(new Date(leer(archivo).vence) > new Date(Date.now() + 30 * DIA),
      "la licencia guardada no extendió el vencimiento");
  });

  await test("manda el token de la licencia, que es con lo que se acredita", async () => {
    // Renovar por email dejaría que cualquiera que lo conozca se lleve
    // la licencia ajena.
    const { dirs } = conLicencia({ token: "tok en&raro" });
    const f = fetchFalso(resp(402, {}));
    await licencia.renovarSiCorresponde(dirs, { fetch: f });
    assert.strictEqual(f.llamadas.length, 1);
    assert.match(f.llamadas[0], /token=tok%20en%26raro/,
      `no mandó el token escapado: ${f.llamadas[0]}`);
  });

  await test("con la licencia lejos de vencer NO sale a la red", async () => {
    // Salir en cada arranque sería un pedido por cliente por día, todo
    // el año, para no hacer nada.
    const { dirs } = conLicencia({ vence: enDias(200) });
    const f = fetchFalso(resp(200, {}));
    const r = await licencia.renovarSiCorresponde(dirs, { fetch: f });
    assert.strictEqual(r.estado, "al-dia");
    assert.strictEqual(f.llamadas.length, 0, "consultó al servidor sin necesidad");
  });

  await test("SIN RED la licencia queda intacta y la app abre igual", async () => {
    // Es el escenario del cliente en una empresa con el firewall cerrado.
    const { dirs, archivo } = conLicencia();
    const f = fetchFalso(new Error("getaddrinfo ENOTFOUND"));
    const r = await licencia.renovarSiCorresponde(dirs, { fetch: f });
    assert.strictEqual(r.estado, "sin-red", "una caída de red no puede propagarse");
    assert.strictEqual(leer(archivo).token, "el-token-del-cliente",
      "se quedó sin licencia por no tener internet");
  });

  await test("SI EL SERVIDOR FALLA (500) no le borra la licencia al cliente", async () => {
    // Un error nuestro no puede convertirse en un cliente bloqueado.
    const { dirs, archivo } = conLicencia();
    const r = await licencia.renovarSiCorresponde(dirs, { fetch: fetchFalso(resp(500, {})) });
    assert.strictEqual(r.estado, "rechazada");
    assert.ok(fs.existsSync(archivo), "borró la licencia por un 500 del servidor");
    assert.strictEqual(leer(archivo).token, "el-token-del-cliente");
  });

  await test("con la suscripción cancelada (402) tampoco la borra: la deja vencer", async () => {
    // Quien canceló pierde el acceso cuando la licencia vence, no antes:
    // pudo haber pagado hasta fin de mes.
    const { dirs, archivo } = conLicencia();
    const r = await licencia.renovarSiCorresponde(dirs, { fetch: fetchFalso(resp(402, {})) });
    assert.strictEqual(r.estado, "rechazada");
    assert.strictEqual(r.codigo, 402);
    assert.strictEqual(leer(archivo).token, "el-token-del-cliente");
  });

  await test("UNA RESPUESTA SIN `vence` NO SE GUARDA", async () => {
    // El bug caro y silencioso: se escribiría encima de la licencia
    // buena, vigente() daría false al instante, y el cliente vería
    // "comprá tu licencia" justo después de renovar bien.
    const { dirs, archivo } = conLicencia();
    const f = fetchFalso(resp(200, { token: "x", licencia: { token: "x", plan: "profesional" } }));
    const r = await licencia.renovarSiCorresponde(dirs, { fetch: f });
    assert.strictEqual(r.estado, "respuesta-invalida");
    assert.strictEqual(leer(archivo).token, "el-token-del-cliente",
      "pisó la licencia buena con una que nace vencida");
  });

  await test("una licencia nueva ya vencida tampoco se guarda", async () => {
    const { dirs, archivo } = conLicencia();
    const f = fetchFalso(resp(200, {
      token: "x", licencia: { token: "x", vence: enDias(-1) } }));
    const r = await licencia.renovarSiCorresponde(dirs, { fetch: f });
    assert.strictEqual(r.estado, "respuesta-invalida");
    assert.strictEqual(leer(archivo).token, "el-token-del-cliente");
  });

  await test("una licencia sin token (comprada antes) no intenta renovar", async () => {
    const { dirs } = conLicencia({ token: undefined });
    const f = fetchFalso(resp(200, {}));
    const r = await licencia.renovarSiCorresponde(dirs, { fetch: f });
    assert.strictEqual(r.estado, "sin-token");
    assert.strictEqual(f.llamadas.length, 0);
  });

  await test("un cliente en prueba (sin licencia) no consulta nada", async () => {
    const datos = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-renov-"));
    const f = fetchFalso(resp(200, {}));
    const r = await licencia.renovarSiCorresponde({ datos, recursos: datos }, { fetch: f });
    assert.strictEqual(r.estado, "sin-licencia");
    assert.strictEqual(f.llamadas.length, 0, "consultó por alguien que nunca compró");
  });

  await test("la puerta de entrada la llama ANTES de mostrar el cartel de compra", () => {
    // Si se llamara después, el que paga todos los meses vería una vez
    // "comprá tu licencia" antes de que la renovación lo rescate.
    const main = fs.readFileSync(path.join(RAIZ, "desktop", "electron", "main.cjs"), "utf8");
    const i = main.indexOf("renovarSiCorresponde");
    const j = main.indexOf("licencia.verificarAcceso()");
    assert.ok(i > 0, "main.cjs nunca llama a renovarSiCorresponde: el endpoint queda sin cliente");
    assert.ok(i < j, "renueva después de chequear el acceso, o sea tarde");
  });

  await test("Electron y Python usan el MISMO margen de renovación", () => {
    // Comparten UNA licencia: si renovaran en momentos distintos, el
    // mismo cliente con las dos versiones vería dos comportamientos.
    const py = fs.readFileSync(path.join(RAIZ, "app-python", "licencia.py"), "utf8");
    const m = py.match(/DIAS_ANTES_DE_RENOVAR\s*=\s*(\d+)/);
    assert.ok(m, "no se pudo leer el margen de licencia.py");
    assert.strictEqual(licencia.DIAS_ANTES_DE_RENOVAR, Number(m[1]),
      `Electron renueva a los ${licencia.DIAS_ANTES_DE_RENOVAR} días y Python a los ${m[1]}`);
  });

  // ── el viaje entero: servidor real → cliente real ─────────────
  await test("LO QUE DEVUELVE EL ENDPOINT ES EXACTAMENTE LO QUE EL CLIENTE SABE GUARDAR", async () => {
    // Las dos mitades se escribieron por separado y por separado las dos
    // parecen bien. Este test es el único que las junta: corre el
    // endpoint de verdad y le pasa su respuesta al cliente de verdad.
    const API = path.join(__dirname, "..", "api");
    const { issueLicense } = require(path.join(API, "_license.js"));
    const ID_SUB = "2c938084726fca480172750000000000";

    const previo = global.fetch;
    global.fetch = async () => ({
      ok: true, status: 200,
      json: async () => ({ id: ID_SUB, status: "authorized",
                           external_reference: "profesional:suscripcion:cliente@empresa.com",
                           payer_email: "cliente@empresa.com" }),
    });

    try {
      const renovarEndpoint = require(path.join(API, "renovar-licencia.js"));
      const tokenViejo = issueLicense({ email: "cliente@empresa.com", plan: "profesional",
                                        mode: "own_ai", paymentId: ID_SUB });

      // 1) El servidor contesta.
      let cuerpo = null, codigo = null;
      const res = { status(c) { codigo = c; return this; }, json(b) { cuerpo = b; return this; } };
      await renovarEndpoint(
        { method: "GET", headers: { host: "mvsqlnlp.com" }, query: { token: tokenViejo } }, res);
      assert.strictEqual(codigo, 200, `el endpoint no renovó: ${JSON.stringify(cuerpo)}`);

      // 2) El cliente guarda esa respuesta tal cual.
      const { dirs, archivo } = conLicencia({ token: tokenViejo });
      const r = await licencia.renovarSiCorresponde(dirs, { fetch: fetchFalso(resp(200, cuerpo)) });
      assert.strictEqual(r.estado, "renovada",
        `el cliente rechazó la respuesta real del servidor: ${JSON.stringify(r)}`);

      // 3) Y lo guardado sirve: tiene todo lo que la app necesita.
      const guardada = leer(archivo);
      for (const campo of ["producto", "email", "plan", "modo", "token", "vence"]) {
        assert.ok(guardada[campo], `a la licencia renovada le falta '${campo}'`);
      }
      assert.ok(new Date(guardada.vence) > new Date(), "la licencia renovada nace vencida");
      assert.strictEqual(guardada.token, cuerpo.token,
        "guardó otra cosa que el token que emitió el servidor");
      // Y ese token guardado tiene que servir para renovar DE NUEVO el
      // mes que viene: si no, la renovación funciona una sola vez.
      const { verifyLicense } = require(path.join(API, "_license.js"));
      assert.strictEqual(verifyLicense(guardada.token).plan, "profesional");
    } finally {
      global.fetch = previo;
    }
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
