/* © 2026 Martín Viera. Todos los derechos reservados. */

/** La landing NO ofrece descarga pública — pide una demo agendada.
 *
 * Hasta acá la landing tenía 4 botones de descarga directa: el .exe de
 * Electron vía GitHub Releases, y el instalador NSIS + el zip
 * autoinstalable servidos desde /downloads/. Cualquiera —cliente real o
 * competencia mirando cómo está armado el producto— se llevaba el
 * artefacto completo sin dejar rastro de quién era.
 *
 * El cambio de criterio: la demo se pide con nombre, país y empresa
 * (/api/solicitar-demo), nunca se descarga sola. Este test es la versión
 * INVERSA del que existía antes (`git log -p` de este archivo tiene el
 * original, que probaba lo contrario a propósito): en vez de confirmar que
 * los links de descarga funcionan, confirma que NO EXISTEN. Si alguien
 * reintroduce un botón de descarga pública sin querer (por ejemplo,
 * copiando el patrón de otra sección), esto lo agarra.
 *
 * El cliente que YA PAGÓ sigue bajando automático — eso no cambió, y por
 * eso no se toca acá: ver flujo-compra.test.js (/api/download,
 * /api/download-licencia, /api/download-instalador) y gracias.test.js.
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

(async () => {
  console.log("\n== La landing no ofrece descarga pública (pide demo agendada) ==");

  await test("ningún link a releases/latest/download en toda la landing", () => {
    const hits = [...LANDING.matchAll(/releases\/latest\/download\/[^"'\s]+/g)].map((m) => m[0]);
    assert.deepStrictEqual(hits, [],
      "volvió un link de descarga directa del Release: " + hits.join(", "));
  });

  await test("ningún link a /downloads/ (zip o exe) en toda la landing", () => {
    const hits = [...LANDING.matchAll(/href="\/downloads\/[^"'\s]+"/g)].map((m) => m[0]);
    assert.deepStrictEqual(hits, [],
      "volvió un link de descarga self-hosted: " + hits.join(", "));
  });

  await test("el formulario de demo existe y postea a /api/solicitar-demo", () => {
    assert.match(LANDING, /id="demoform"/, "no está el <form id=\"demoform\">");
    assert.match(LANDING, /fetch\(['"]\/api\/solicitar-demo['"]/,
      "el form no llama a /api/solicitar-demo");
  });

  await test("el form de demo pide nombre, país, empresa y email", () => {
    for (const campo of ['name="nombre"', 'name="pais"', 'name="empresa"', 'name="email"']) {
      assert.ok(LANDING.includes(campo), `falta el campo ${campo} en el form de demo`);
    }
  });

  await test("el .exe del dueño NUNCA llega a un Release PÚBLICO", () => {
    // Sigue vigente aunque cambie el modelo de descarga: la build del
    // propietario lleva licencia embebida hasta 2099. Un Release público
    // la deja a un clic de cualquiera.
    //
    // La regla es "nunca a un Release público", no "nunca a un Release":
    // con el repositorio privado, ese asset es justamente cómo el dueño
    // baja la versión completa para probar (ver owner/INSTALADOR.md). Lo
    // que se exige entonces es que CADA upload del .exe del propietario
    // esté condicionado a que el repositorio sea privado — un upload sin
    // esa guarda es exactamente el bug que este test existe para frenar.
    const sinGuarda = [];
    for (const m of WORKFLOW.matchAll(/gh release upload[^\n]*/g)) {
      if (!/OWNER/i.test(m[0])) continue;
      const inicioPaso = WORKFLOW.lastIndexOf("\n      - name:", m.index);
      const bloque = WORKFLOW.slice(inicioPaso, m.index);
      if (!/if:\s*github\.event\.repository\.private/.test(bloque)) {
        sinGuarda.push(m[0].trim());
      }
    }
    assert.deepStrictEqual(sinGuarda, [],
      "build-desktop.yml sube la versión sin trial a un Release sin exigir " +
      "que el repositorio sea privado: " + sinGuarda.join(" | "));
  });

  await test("la landing no menciona el .exe del dueño en ningún lado", () => {
    const hits = LANDING.match(/OWNER/gi) || [];
    assert.deepStrictEqual(hits, [], "la landing pública menciona la build del propietario");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
