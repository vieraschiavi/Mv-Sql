/** Trial y licencia de la app Electron (desktop/electron/services/licencia.cjs).
 *
 * Hasta que existió ese módulo, el desktop NO tenía ningún control: el .exe
 * publicado en Releases era el producto completo, gratis y sin vencimiento.
 * El trial de 7 días que vende la web se hacía cumplir solo en el producto
 * Python. O sea que la diferencia entre "demo" y "versión oficial" no
 * existía en el binario que más se descarga.
 *
 * Lo que se fija acá son los caminos donde el negocio se pierde en silencio:
 * la app abre igual y nadie se entera de que dejó de cobrar.
 *
 *   1. El trial se ACABA. Parece obvio, pero un off-by-one en el conteo de
 *      días regala una licencia perpetua sin que falle nada.
 *   2. Editar la marca a mano no estira el trial. La firma no cierra, se
 *      descarta el archivo y arranca un trial nuevo — el tramposo queda
 *      peor que antes, no mejor.
 *   3. Atrasar el reloj no revive el trial.
 *   4. Una licencia VENCIDA no da acceso (si la comparación de fechas se
 *      invierte, todos los clientes vencidos siguen entrando gratis).
 *   5. La build owner abre sin pedir nada, que es su razón de ser.
 *
 * Vive en web/tests/ porque es el único árbol que el runner descubre para
 * Node, igual que desktop-solo-lectura.test.js. El módulo resuelve sus
 * rutas tarde y las acepta inyectadas, así que corre sin levantar Electron.
 */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const lic = require(
  path.join(__dirname, "..", "..", "desktop", "electron", "services", "licencia.cjs"));

const DIA = 86400000;

/** Directorios limpios por caso, para que un test no herede el trial de otro. */
function entorno() {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-lic-"));
  const dirs = { datos: path.join(base, "datos"), recursos: path.join(base, "recursos") };
  fs.mkdirSync(dirs.datos, { recursive: true });
  fs.mkdirSync(dirs.recursos, { recursive: true });
  return dirs;
}

function marcaTrial(dirs, hace_dias) {
  const inicio = new Date(Date.now() - hace_dias * DIA).toISOString();
  fs.writeFileSync(path.join(dirs.datos, ".mvsql_trial.json"),
    JSON.stringify({ inicio, firma: lic._firma(inicio) }));
  return inicio;
}

function licencia(dirs, archivo, dias_hasta_vencer) {
  fs.writeFileSync(path.join(dirs.datos, archivo), JSON.stringify(
    { producto: "MV SQL NLP", vence: new Date(Date.now() + dias_hasta_vencer * DIA).toISOString() }));
}

(async () => {
  console.log("\n== Trial y licencia del desktop (Electron) ==");

  await test("primer arranque: entra, con los 7 días completos", () => {
    const dirs = entorno();
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.permitido, true);
    assert.strictEqual(r.diasRestantes, 7);
    assert.strictEqual(r.conLicencia, false);
  });

  await test("el primer arranque deja la marca (si no, el trial no arranca nunca)", () => {
    const dirs = entorno();
    lic.verificarAcceso(dirs);
    assert.ok(fs.existsSync(path.join(dirs.datos, ".mvsql_trial.json")),
      "no se escribió la marca: cada arranque volvería a dar 7 días");
  });

  await test("a mitad del trial descuenta los días transcurridos", () => {
    const dirs = entorno();
    marcaTrial(dirs, 3);
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.permitido, true);
    assert.strictEqual(r.diasRestantes, 4);
  });

  await test("EL TRIAL SE ACABA: al día 7 ya no entra", () => {
    const dirs = entorno();
    marcaTrial(dirs, 7);
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.permitido, false, "el trial no corta: es una licencia perpetua gratis");
    assert.strictEqual(r.diasRestantes, 0);
  });

  await test("y sigue cortado mucho después", () => {
    const dirs = entorno();
    marcaTrial(dirs, 400);
    assert.strictEqual(lic.verificarAcceso(dirs).permitido, false);
  });

  await test("editar la fecha a mano NO estira el trial (firma inválida)", () => {
    const dirs = entorno();
    // El tramposo se pone una fecha de inicio en el futuro para tener más días.
    fs.writeFileSync(path.join(dirs.datos, ".mvsql_trial.json"), JSON.stringify(
      { inicio: new Date(Date.now() + 90 * DIA).toISOString(), firma: "firma-inventada" }));
    const r = lic.verificarAcceso(dirs);
    // Se descarta y arranca un trial nuevo: 7 días, no 97.
    assert.strictEqual(r.diasRestantes, 7);
    const guardado = JSON.parse(fs.readFileSync(path.join(dirs.datos, ".mvsql_trial.json"), "utf8"));
    assert.strictEqual(guardado.firma, lic._firma(guardado.inicio),
      "quedó una marca sin firma válida");
  });

  await test("atrasar el reloj no revive el trial", () => {
    const dirs = entorno();
    // Marca legítima con inicio en el futuro = el reloj se movió para atrás.
    marcaTrial(dirs, -5);
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.permitido, false, "adelantar/atrasar el reloj regala trial");
  });

  await test("una licencia vigente saltea el trial aunque esté vencido", () => {
    const dirs = entorno();
    marcaTrial(dirs, 400);
    licencia(dirs, "licencia_mvsql.json", 30);
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.permitido, true);
    assert.strictEqual(r.conLicencia, true);
    assert.strictEqual(r.diasRestantes, null, "con licencia no corresponde contar días de trial");
  });

  await test("UNA LICENCIA VENCIDA NO DA ACCESO", () => {
    const dirs = entorno();
    marcaTrial(dirs, 400);
    licencia(dirs, "licencia_mvsql.json", -1);
    assert.strictEqual(lic.verificarAcceso(dirs).permitido, false,
      "los clientes vencidos siguen entrando: la renovación no se cobra nunca");
  });

  await test("una licencia corrupta no abre la puerta", () => {
    const dirs = entorno();
    marcaTrial(dirs, 400);
    fs.writeFileSync(path.join(dirs.datos, "licencia_mvsql.json"), "{no es json");
    assert.strictEqual(lic.verificarAcceso(dirs).permitido, false);
  });

  await test("la build owner abre sin pedir nada", () => {
    const dirs = entorno();
    marcaTrial(dirs, 400);   // trial agotado
    fs.writeFileSync(path.join(dirs.recursos, "licencia_owner.json"), JSON.stringify(
      { plan: "propietario", vence: "2099-12-31T00:00:00+00:00" }));
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.permitido, true);
    assert.strictEqual(r.esPropietario, true);
  });

  await test("una licencia con BOM igual se lee (la escribe PowerShell)", () => {
    // El runner de Windows genera licencia_owner.json con PowerShell, que
    // segun la version le antepone un BOM. JSON.parse lo rechaza, y como
    // el error se traga el catch, la build del propietario mostraria el
    // trial sin ningun sintoma que explique por que.
    const dirs = entorno();
    marcaTrial(dirs, 400);
    fs.writeFileSync(path.join(dirs.recursos, "licencia_owner.json"),
      "\ufeff" + JSON.stringify({ plan: "propietario", vence: "2099-12-31T00:00:00+00:00" }));
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.permitido, true, "el BOM invalido la licencia del propietario");
    assert.strictEqual(r.esPropietario, true);
  });

  await test("la build normal NO trae licencia de propietario", () => {
    // Si el archivo se colara en la build de clientes, todos tendrían
    // acceso hasta 2099. Es el mismo error que el .exe OWNER en el Release.
    const dirs = entorno();
    const r = lic.verificarAcceso(dirs);
    assert.strictEqual(r.esPropietario, false);
  });

  await test("instalarLicencia guarda una válida y rechaza una vencida", () => {
    const dirs = entorno();
    const buena = JSON.stringify({ vence: new Date(Date.now() + 30 * DIA).toISOString() });
    assert.strictEqual(lic.instalarLicencia(buena, dirs).ok, true);
    assert.strictEqual(lic.verificarAcceso(dirs).conLicencia, true);

    const dirs2 = entorno();
    const vieja = JSON.stringify({ vence: new Date(Date.now() - DIA).toISOString() });
    assert.strictEqual(lic.instalarLicencia(vieja, dirs2).ok, false);
    assert.strictEqual(lic.instalarLicencia("{roto", dirs2).ok, false);
  });

  await test("el trial dura lo mismo que en el producto Python", () => {
    // Son dos implementaciones del mismo trial. Si una dice 7 y la otra 14,
    // el cliente que prueba las dos ve algo incoherente y nosotros no
    // sabemos cuál es la promesa real de la web.
    const py = fs.readFileSync(
      path.join(__dirname, "..", "..", "app-python", "licencia.py"), "utf8");
    const m = py.match(/TRIAL_DIAS\s*=\s*(\d+)/);
    assert.ok(m, "no se pudo leer TRIAL_DIAS de licencia.py");
    assert.strictEqual(lic.TRIAL_DIAS, Number(m[1]),
      `Electron da ${lic.TRIAL_DIAS} días y Python ${m[1]}`);
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
