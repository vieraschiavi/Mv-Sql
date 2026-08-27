/* © 2026 Martín Viera. Todos los derechos reservados. */

/** El release automático solo dispara cuando hay versión nueva.
 *
 * build-desktop.yml corre en push a main, así que sin una condición que lo
 * frene cada merge intentaría publicar OTRA VEZ la misma versión: rehace el
 * Release del tag vigente, vuelve a subir los .exe y reemplaza los assets
 * que la web está enlazando en ese momento. Un merge de una coma en el
 * README republicaría el producto.
 *
 * La condición vive repartida entre el job "decidir" (que consulta si ya
 * existe un Release para la versión de desktop/package.json) y los "if" de
 * los jobs que compilan. Con sacar cualquiera de las dos partes se rompe, y
 * se rompe en silencio: el workflow queda en verde igual — solo que
 * publicando de más. Por eso están fijadas acá las dos.
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const RUTA = path.join(RAIZ, ".github", "workflows", "build-desktop.yml");
const CRUDO = fs.readFileSync(RUTA, "utf-8");
const WF = yaml.load(CRUDO);
// En YAML, "on:" sin comillas se parsea como el booleano true.
const ON = WF.on || WF[true];

// Los jobs que producen y publican artefactos. "decidir" no está: es el
// que decide, no puede depender de sí mismo.
const JOBS_QUE_PUBLICAN = Object.keys(WF.jobs).filter((j) => j !== "decidir");

(async () => {
  console.log("\n== Release automático: solo con versión nueva ==");

  await test("nadie pasa config a electron-builder con la sintaxis -c.clave", () => {
    // "-c.nsis.artifactName=X" parece un override de config y no lo es:
    // electron-builder lee "-c" como la RUTA de un archivo de config y
    // busca uno llamado ".nsis.artifactName=X". Rompió un release entero
    // con un ENOENT de un archivo que nadie escribió nunca:
    //   ENOENT: open '...\desktop\.nsis.artifactName=MV-SQL-NLP-App-Setup-OWNER.exe'
    // Falla rápido y con exit 1, así que se lleva puesto el job entero.
    // Se saltean los comentarios: el YAML documenta este mismo error para
    // que no se repita, y el guard no puede dispararse con su propia
    // explicación.
    const malos = CRUDO.split("\n")
      .filter((l) => !l.trim().startsWith("#"))
      .filter((l) => /-c\.[a-zA-Z]/.test(l));
    assert.deepStrictEqual(malos.map((l) => l.trim()), [],
      "electron-builder va a leer eso como una ruta de archivo, no como config");
  });

  await test("el instalador del propietario se renombra y solo va al Release si el repo es privado", () => {
    // Sale del build con el mismo nombre que el del cliente. Si el
    // renombrado no estuviera, quedaría un .exe con licencia hasta 2099
    // llamado igual que el que baja cualquiera.
    assert.ok(/MV-SQL-NLP-App-Setup-OWNER\.exe/.test(CRUDO),
      "no se renombra el instalador del propietario");
    // Con el repositorio privado ese asset es cómo el dueño baja la versión
    // completa (ver owner/INSTALADOR.md); en uno público sería regalar el
    // producto. Se exige la guarda, no la ausencia del upload.
    for (const m of CRUDO.matchAll(/gh release upload[^\n]*/g)) {
      if (!/OWNER/i.test(m[0])) continue;
      const inicioPaso = CRUDO.lastIndexOf("\n      - name:", m.index);
      assert.match(CRUDO.slice(inicioPaso, m.index),
        /if:\s*github\.event\.repository\.private/,
        "se sube la build del propietario al Release sin exigir repo privado: " +
        m[0].trim());
    }
  });

  await test("el workflow dispara en push a main", () => {
    assert.ok(ON.push && (ON.push.branches || []).includes("main"),
      "ya no corre en push a main — ¿se volvió al disparo manual?");
  });

  await test("existe el job que decide si hay algo para publicar", () => {
    assert.ok(WF.jobs.decidir, "no está el job 'decidir'");
    assert.ok(WF.jobs.decidir.outputs && WF.jobs.decidir.outputs.seguir,
      "'decidir' no expone el output 'seguir' que miran los demás");
  });

  await test("decidir CONSULTA si el Release ya existe, no adivina", () => {
    // Comparar contra un valor escrito a mano en el YAML se desincroniza
    // solo. La única fuente confiable es la API.
    const pasos = JSON.stringify(WF.jobs.decidir.steps);
    assert.ok(/gh release view/.test(pasos),
      "'decidir' no le pregunta a la API si el Release existe");
    assert.ok(/desktop\/package\.json/.test(pasos),
      "'decidir' no lee la versión de desktop/package.json");
  });

  await test("TODO job que publica está detrás de decidir", () => {
    const sueltos = JOBS_QUE_PUBLICAN.filter((j) => {
      const necesita = [WF.jobs[j].needs || []].flat();
      // O depende de 'decidir', o depende de alguien que ya depende de él.
      return !necesita.includes("decidir") &&
        !necesita.some((n) => [WF.jobs[n]?.needs || []].flat().includes("decidir"));
    });
    assert.deepStrictEqual(sueltos, [],
      "estos jobs corren sin pasar por 'decidir': " + sueltos.join(", "));
  });

  await test("los jobs que arrancan la cadena chequean el output", () => {
    // Los que dependen de 'decidir' directamente son los únicos que pueden
    // frenar la cadena; los de más abajo se saltean solos por needs.
    const directos = JOBS_QUE_PUBLICAN.filter(
      (j) => [WF.jobs[j].needs || []].flat().includes("decidir"));
    assert.ok(directos.length > 0, "ningún job depende de 'decidir'");
    for (const j of directos) {
      assert.ok(/needs\.decidir\.outputs\.seguir/.test(WF.jobs[j].if || ""),
        `${j} depende de 'decidir' pero no mira su resultado: corre igual`);
    }
  });

  await test("un disparo explícito (tag o a mano) publica igual", () => {
    // El freno es solo para el push a main. Si alguien corre el workflow a
    // propósito, rehacer un Release existente es lo que está pidiendo.
    const pasos = JSON.stringify(WF.jobs.decidir.steps);
    assert.ok(/workflow_dispatch/.test(pasos) && /ref_type/.test(pasos),
      "'decidir' no exceptúa el disparo manual ni el de tag: correrlo a " +
      "mano sobre una versión ya publicada no haría nada");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
