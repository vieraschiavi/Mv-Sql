/* © 2026 Martín Viera. Todos los derechos reservados. */

/** El instalador lleva TODOS los módulos del producto Python.
 *
 * `installer/mvsql.nsi` lista los archivos uno por uno (`File "...\x.py"`),
 * no con un comodín. Es a propósito —así no se cuela al instalador un
 * archivo suelto de la carpeta de desarrollo— pero tiene un costo: cada
 * módulo nuevo hay que agregarlo a mano, y olvidarse NO rompe nada acá.
 *
 * Rompe en la máquina del cliente, después de pagar, con un ImportError
 * apenas abre. Nada de lo que corre en este repo lo detecta: los tests
 * importan desde app-python/, donde el archivo sí está; el zip se arma
 * con otra lista; la app arranca perfecto en desarrollo.
 *
 * Pasó con frescura.py, el módulo del panel de frescura de datos: quedó
 * fuera del instalador y solo apareció al revisar el .nsi a mano.
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const NSI = fs.readFileSync(path.join(RAIZ, "installer", "mvsql.nsi"), "utf8");
const SRC = path.join(RAIZ, "app-python");

// Módulos que NO tienen por qué ir al instalador del cliente.
const FUERA = new Set([
  "generar_db_demo.py",   // sí va, pero se valida aparte más abajo
]);

/** Los .py del producto (sin tests ni utilidades de desarrollo). */
function modulosDelProducto() {
  return fs.readdirSync(SRC)
    .filter((f) => f.endsWith(".py"))
    .filter((f) => !f.startsWith("_"))
    .sort();
}

/** ¿El .nsi copia este archivo, sea por nombre o por comodín? */
function loInstala(archivo) {
  if (NSI.includes(`\\${archivo}"`)) return true;
  // Comodines como  File /nonfatal "${APP_SRC}\licencia*.py"
  for (const m of NSI.matchAll(/File\s+(?:\/nonfatal\s+)?"\$\{APP_SRC\}\\([^"]+)"/g)) {
    const patron = m[1];
    if (!patron.includes("*")) continue;
    const re = new RegExp("^" + patron.replace(/\./g, "\\.").replace(/\*/g, ".*") + "$");
    if (re.test(archivo)) return true;
  }
  return false;
}

(async () => {
  console.log("\n== El instalador lleva todos los módulos del producto ==");

  await test("HAY ALGO QUE COMPARAR (si no, este archivo no prueba nada)", () => {
    const mods = modulosDelProducto();
    assert.ok(mods.length > 8, `solo ${mods.length} módulos en app-python/: ¿ruta mal?`);
    assert.ok(/File\s+"\$\{APP_SRC\}/.test(NSI), "el .nsi no copia nada de app-python");
  });

  await test("NINGÚN MÓDULO QUEDA FUERA DEL INSTALADOR", () => {
    const faltan = modulosDelProducto()
      .filter((f) => !FUERA.has(f))
      .filter((f) => !loInstala(f));
    assert.deepStrictEqual(faltan, [],
      "estos módulos existen en app-python/ pero el instalador NO los copia, " +
      "así que la app instalada revienta con ImportError al abrir: " +
      faltan.join(", ") + " — agregalos a installer/mvsql.nsi");
  });

  await test("el instalador no lista archivos que ya no existen", () => {
    // El error espejo: se borra o renombra un módulo y el .nsi queda
    // pidiendo un archivo que no está. makensis falla al compilar, pero
    // recién cuando alguien arma el instalador.
    const fantasmas = [];
    for (const m of NSI.matchAll(/File\s+"\$\{APP_SRC\}\\([^"*]+)"/g)) {
      if (!fs.existsSync(path.join(SRC, m[1]))) fantasmas.push(m[1]);
    }
    assert.deepStrictEqual(fantasmas, [],
      `el instalador copia archivos que no existen: ${fantasmas.join(", ")}`);
  });

  // NOTA: acá hubo un cuarto caso que comparaba el instalador contra
  // tools/empaquetar_zip.py, asumiendo que los .py nombrados ahí eran
  // exclusiones. No lo son: son MODULOS_PROTEGIDOS, los que build_cython
  // compila a .pyd. El caso fallaba por una premisa equivocada, no por un
  // problema real, y se sacó en vez de retorcerlo hasta que pasara. La
  // paridad zip/instalador la cubre zip-al-dia.test.js por otro camino.

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
