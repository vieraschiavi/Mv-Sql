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
