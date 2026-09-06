/* © 2026 Martín Viera. Todos los derechos reservados. */

/** Modo portable: en la máquina del cliente no queda nada.
 *
 * Hay dos escenarios de instalación y son distintos de verdad:
 * instalada en la máquina propia (los datos van a %APPDATA% y sobreviven
 * a las actualizaciones), y portable en la VM o la laptop de un cliente
 * (los datos van al lado del .exe y se borran sacando la carpeta).
 *
 * Hasta este cambio "portable" solo quería decir que no hacía falta
 * instalador: la app igual escribía en %APPDATA% de ESA máquina las
 * conexiones guardadas, una copia de la base importada del cliente, la
 * licencia y la marca de trial — más el caché y las cookies que Electron
 * guarda por su cuenta. Trabajando de consultor, eso es dejarle al
 * cliente sus propios datos y tu licencia en un perfil que no es tuyo.
 *
 * Este archivo fija las dos mitades: que la portable redirija, y que la
 * instalación normal NO se toque (si se redirigiera siempre, cada
 * actualización perdería las conexiones guardadas del usuario).
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

const RUTAS = path.join(__dirname, "..", "..", "desktop", "electron", "services", "rutas.cjs");
const rutas = require(RUTAS);

// app de mentira: registra qué ruta le setearon, sin levantar Electron.
function appFalsa() {
  const a = { seteadas: {}, userData: "C:\\Users\\yo\\AppData\\Roaming\\MV SQL NLP" };
  a.setPath = (k, v) => { a.seteadas[k] = v; if (k === "userData") a.userData = v; };
  a.getPath = (k) => (k === "userData" ? a.userData : null);
  return a;
}

(async () => {
  console.log("\n== Portable: nada queda en la máquina del cliente ==");

  await test("INSTALACIÓN NORMAL: no se toca la carpeta de datos de siempre", () => {
    // Sin PORTABLE_EXECUTABLE_DIR estamos en una instalación común. Si acá
    // se redirigiera, cada actualización dejaría las conexiones guardadas
    // del usuario en la carpeta vieja y parecería que se perdieron.
    const app = appFalsa();
    const antes = app.userData;
    const r = rutas.configurarCarpetaDatos(app, {});
    assert.strictEqual(r, null, "no debe redirigir en una instalación normal");
    assert.strictEqual(app.userData, antes, "cambió la carpeta de datos de una instalación normal");
    assert.deepStrictEqual(app.seteadas, {}, "no debería haber llamado a setPath");
  });

  await test("PORTABLE: los datos van AL LADO DEL .EXE, no a %APPDATA%", () => {
    const base = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-portable-"));
    const app = appFalsa();
    const r = rutas.configurarCarpetaDatos(app, { PORTABLE_EXECUTABLE_DIR: base });
    assert.ok(r, "debía devolver la carpeta configurada");
    assert.strictEqual(r, path.join(base, rutas.SUBCARPETA));
    assert.strictEqual(app.userData, r, "no redirigió el userData de Electron");
    assert.ok(!/AppData|Roaming/i.test(app.userData),
      `la carpeta portable sigue apuntando al perfil del usuario: ${app.userData}`);
    fs.rmSync(base, { recursive: true, force: true });
  });

  await test("la carpeta se crea sola (el .exe puede correr en una carpeta vacía)", () => {
    const base = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-portable-"));
    rutas.configurarCarpetaDatos(appFalsa(), { PORTABLE_EXECUTABLE_DIR: base });
    assert.ok(fs.existsSync(path.join(base, rutas.SUBCARPETA)),
      "no creó la carpeta de datos: la primera escritura fallaría");
    fs.rmSync(base, { recursive: true, force: true });
  });

  await test("SE REDIRIGE EL userData DE ELECTRON, no cada archivo por su cuenta", () => {
    // Es la diferencia entre tapar la mitad del problema y resolverlo:
    // moviendo userData se mueve también lo que Electron guarda solo
    // (caché, cookies, Local Storage), que ningún módulo controla y es
    // lo que de verdad deja rastro en la máquina del cliente.
    const base = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-portable-"));
    const app = appFalsa();
    rutas.configurarCarpetaDatos(app, { PORTABLE_EXECUTABLE_DIR: base });
    assert.strictEqual(app.seteadas.userData, path.join(base, rutas.SUBCARPETA),
      "no se llamó a app.setPath('userData', ...)");
    fs.rmSync(base, { recursive: true, force: true });
  });

  await test("si no se puede escribir al lado del .exe, la app ABRE IGUAL", () => {
    // Pendrive de solo lectura o carpeta bloqueada por política de la
    // empresa: preferimos que ande (dejando rastro, avisando en consola)
    // a que no abra en medio de una visita al cliente.
    // Se apunta a un ARCHIVO en vez de una carpeta: crear un subdirectorio
    // adentro falla al instante con ENOTDIR. Es determinista y no depende
    // de permisos del sistema donde corran los tests.
    const archivo = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-ro-")), "soy-un-archivo");
    fs.writeFileSync(archivo, "");
    const app = appFalsa();
    const antes = app.userData;
    const r = rutas.configurarCarpetaDatos(app, { PORTABLE_EXECUTABLE_DIR: archivo });
    assert.strictEqual(r, null, "debía caer a la carpeta de usuario");
    assert.strictEqual(app.userData, antes);
    fs.rmSync(path.dirname(archivo), { recursive: true, force: true });
  });

  await test("main.cjs LO LLAMA ANTES de cargar los módulos que escriben en disco", () => {
    // Si se llamara después, esos módulos ya resolvieron su ruta contra
    // el userData viejo y los datos quedan partidos entre las dos
    // carpetas — el peor de los dos mundos.
    const crudo = fs.readFileSync(
      path.join(__dirname, "..", "..", "desktop", "electron", "main.cjs"), "utf8");
    // Se descartan los comentarios ANTES de buscar. Buscar el nombre suelto
    // da un falso positivo: comentar la llamada la deja escrita igual, y el
    // test seguiría en verde con el modo portable desactivado. (Se verificó
    // comentándola: sin este filtro, la mutación no se detecta.)
    const main = crudo
      .split("\n")
      .filter((l) => !l.trim().startsWith("//"))
      .join("\n");
    const llamada = main.search(/^\s*(?:const\s+\w+\s*=\s*)?rutas\.configurarCarpetaDatos\(/m);
    assert.ok(llamada >= 0,
      "main.cjs no llama a configurarCarpetaDatos(): el modo portable no se activa " +
      "y la build portable vuelve a escribir en %APPDATA% de la máquina del cliente");
    for (const mod of ["services/db.cjs", "services/store.cjs", "services/licencia.cjs"]) {
      const i = main.indexOf(mod);
      assert.ok(i > llamada,
        `main.cjs carga ${mod} ANTES de configurar la carpeta de datos`);
    }
  });

  await test("los tres archivos con datos del cliente cuelgan del userData", () => {
    // Si alguno se escribiera con una ruta propia, se saltearía la
    // redirección y seguiría cayendo en %APPDATA% del cliente.
    const dir = path.join(__dirname, "..", "..", "desktop", "electron", "services");
    for (const [archivo, dato] of [
      ["store.cjs", "mvsql-store.json (conexiones guardadas)"],
      ["db.cjs", "importado.db (copia de la base del cliente)"],
      ["licencia.cjs", "licencia_mvsql.json"],
    ]) {
      const src = fs.readFileSync(path.join(dir, archivo), "utf8");
      assert.match(src, /getPath\(["']userData["']\)/,
        `${archivo} no resuelve ${dato} contra userData: se saltea el modo portable`);
    }
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
