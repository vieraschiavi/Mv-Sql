/** Los botones de descarga apuntan a archivos que existen de verdad.
 *
 * La landing reparte las descargas en DOS canales, por tamaño:
 *
 *   a) Self-hosted (`/downloads/<archivo>`): el zip autoinstalable y el
 *      instalador NSIS del producto Python. Pesan pocos cientos de KB, viven
 *      commiteados en web/downloads/ y Vercel los sirve estáticos. No
 *      dependen de que exista ningún Release: funcionan apenas deploya.
 *
 *   b) GitHub Releases (`releases/latest/download/<archivo>`): el instalador
 *      Electron, que ronda los 90 MB y por eso no puede vivir en el repo.
 *
 * Cada canal se rompe distinto, y este test cubre los dos:
 *
 *   1. Self-hosted: el link apunta a un archivo que no está en web/downloads/.
 *      Da 404 en producción y acá se detecta mirando el disco.
 *
 *   2. Release: el nombre que enlaza la web no es el que sube el workflow.
 *      Renombrar el .exe en build-desktop.yml y olvidarse de la landing (o al
 *      revés) deja el botón roto incluso con el Release publicado y en verde.
 *
 * El caso 2 es especialmente traicionero porque todo "parece" funcionar: el
 * workflow termina bien, el Release existe y tiene assets. Solo falla el
 * cliente que hace clic.
 *
 * Queda fuera de este test un tercer modo de falla, que es operativo y no se
 * puede ver offline: que no haya Release publicado, o que el único sea un
 * borrador (GitHub no resuelve los drafts en /releases/latest). Va con su
 * comando de verificación en docs/DESPLIEGUE.md.
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

// Lo que la landing sirve por su cuenta, desde web/downloads/.
const AUTOSERVIDOS = [...new Set(
  [...LANDING.matchAll(/href="\/downloads\/([^"'\s]+)"/g)].map((m) => m[1]))];
const DIR_DOWNLOADS = path.join(RAIZ, "web", "downloads");

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

  await test("los botones self-hosted apuntan a archivos que están en web/downloads/", () => {
    assert.ok(AUTOSERVIDOS.length > 0,
      "ningún botón sirve desde /downloads/ — ¿volvieron todos a depender del Release?");
    console.log(`      self-hosted: ${AUTOSERVIDOS.join(", ")}`);
    const faltantes = AUTOSERVIDOS.filter(
      (f) => !fs.existsSync(path.join(DIR_DOWNLOADS, f)));
    assert.deepStrictEqual(faltantes, [],
      "la web enlaza /downloads/<archivo> que no existe en el repo: " +
      faltantes.join(", ") + " (404 en producción apenas deploye)");
  });

  await test("los archivos self-hosted no van vacíos", () => {
    // Un placeholder de 0 bytes deploya igual y el cliente se baja la nada.
    for (const f of AUTOSERVIDOS) {
      const bytes = fs.statSync(path.join(DIR_DOWNLOADS, f)).size;
      assert.ok(bytes > 1024, `${f} pesa ${bytes} bytes: no es un instalador real`);
    }
  });

  await test("ningún botón self-hosted sirve la build del dueño", () => {
    const filtrado = AUTOSERVIDOS.filter((f) => /OWNER/i.test(f));
    assert.deepStrictEqual(filtrado, [],
      "la landing pública sirve la versión sin restricciones del dueño");
  });

  await test("el .exe del dueño NO se sube al Release (el repo es público)", () => {
    // La build del propietario lleva licencia embebida hasta 2099 y exenta
    // del trial. Un Release de un repo público lo deja a un clic de
    // cualquiera: sería regalar el producto pago, sin vencimiento.
    // Mientras electron-builder dejaba los Releases en borrador esto era
    // privado de hecho; releaseType: release lo volvió público sin tocar
    // el 'gh release upload'. Va como artefacto de Actions, que sí exige
    // acceso al repo.
    const subeOwner = [...WORKFLOW.matchAll(/gh release upload[^\n]*/g)]
      .map((m) => m[0])
      .filter((l) => /OWNER/i.test(l));
    assert.deepStrictEqual(subeOwner, [],
      "build-desktop.yml sube la versión sin trial a un Release público: " +
      subeOwner.join(" | "));
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
