/** Los botones de descarga apuntan a archivos que el release SÍ publica.
 *
 * Los tres botones de la landing enlazan a
 * github.com/.../releases/latest/download/<archivo>. Ese link da 404 por dos
 * motivos distintos, y conviene no confundirlos:
 *
 *   1. No hay Release publicado (o el único es un borrador — GitHub no
 *      resuelve los drafts en /releases/latest). Es un paso operativo, va en
 *      docs/DESPLIEGUE.md con su comando de verificación; no se puede probar
 *      desde acá sin red.
 *
 *   2. El nombre del archivo que enlaza la web no es el que sube el workflow.
 *      Ese SÍ se detecta offline, y es el que este test fija: renombrar el
 *      .exe en build-desktop.yml y olvidarse de la landing (o al revés) deja
 *      los botones rotos incluso con el Release publicado y en verde.
 *
 * El caso 2 es especialmente traicionero porque todo "parece" funcionar: el
 * workflow termina bien, el Release existe y tiene assets. Solo falla el
 * cliente que hace clic.
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
const LANDING = fs.readFileSync(path.join(RAIZ, "web", "index.html"), "utf-8");
const WORKFLOW = fs.readFileSync(
  path.join(RAIZ, ".github", "workflows", "build-desktop.yml"), "utf-8");
const EBUILDER = fs.readFileSync(
  path.join(RAIZ, "desktop", "electron-builder.yml"), "utf-8");

// Lo que la landing le pide al Release.
const ENLAZADOS = [...new Set(
  [...LANDING.matchAll(/releases\/latest\/download\/([^"'\s]+)/g)].map((m) => m[1]))];

// El Release recibe assets por DOS vías, no una:
//   a) los 'gh release upload <tag> <ruta>' explícitos del workflow (el
//      producto Python: zip autoinstalable + instalador .exe NSIS).
//   b) electron-builder con --publish=always sube el instalador de la app
//      Electron con el nombre que fija su artifactName en electron-builder.yml.
// Mirar solo (a) daba un falso 404 para el .exe nativo, que sí termina en el
// Release aunque ningún 'gh release upload' lo nombre.
const SUBIDOS_GH = [...WORKFLOW.matchAll(/gh release upload[^\n]*?([\w.-]+\.(?:exe|zip))/g)]
  .map((m) => m[1]);
const SUBIDOS_EBUILDER = [...EBUILDER.matchAll(/artifactName:\s*["']([^"']+)["']/g)]
  .map((m) => m[1])
  // Los nombres con ${version} no se pueden enlazar de forma estable desde la
  // web (cambian en cada release); electron-builder los sube igual, pero la
  // landing nunca los referencia, así que no aportan a este chequeo.
  .filter((n) => !n.includes("${version}"))
  .map((n) => n.replace("${ext}", "exe"));
const SUBIDOS = [...new Set([...SUBIDOS_GH, ...SUBIDOS_EBUILDER])];

(async () => {
  console.log("\n== Botones de descarga vs assets del Release ==");

  await test("la landing enlaza al menos un archivo del Release", () => {
    assert.ok(ENLAZADOS.length > 0,
      "ningún link a releases/latest/download — ¿cambió la forma de distribuir?");
    console.log(`      landing pide: ${ENLAZADOS.join(", ")}`);
  });

  await test("el workflow sube al menos un archivo", () => {
    assert.ok(SUBIDOS.length > 0,
      "no se encontró ningún 'gh release upload' en build-desktop.yml");
    console.log(`      workflow sube: ${SUBIDOS.join(", ")}`);
  });

  await test("TODO lo que la landing enlaza es algo que el workflow sube", () => {
    const huerfanos = ENLAZADOS.filter((f) => !SUBIDOS.includes(f));
    assert.deepStrictEqual(huerfanos, [],
      "la web enlaza archivos que el Release nunca va a tener: " +
      huerfanos.join(", ") + " (el botón daría 404 con el Release publicado)");
  });

  await test("los nombres no llevan la versión adentro (romperían en cada release)", () => {
    // Un "MV-SQL-NLP-Setup-1.2.3.exe" obliga a editar la landing en cada
    // versión. El .nsi ya usa nombre estable a propósito; esto lo fija.
    for (const f of ENLAZADOS) {
      assert.ok(!/\d+\.\d+/.test(f),
        `${f} lleva número de versión: el link se rompe en la próxima release`);
    }
  });

  await test("el .exe del dueño NO se ofrece en la web pública", () => {
    // La build OWNER no tiene límite de prueba: se distribuye solo como asset
    // de GitHub para uso propio, nunca desde la landing.
    const filtrado = ENLAZADOS.filter((f) => /OWNER/i.test(f));
    assert.deepStrictEqual(filtrado, [],
      "la landing pública ofrece la versión sin restricciones del dueño");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
