// correr-tests.mjs — corre TODA la suite del repo con un solo comando.
// ===================================================================
// Antes había que acordarse de tres comandos distintos (los tests de
// web/, y los dos de app-python/ uno por uno). Peor: web/package.json
// listaba los archivos de test a mano, así que agregar un test nuevo y
// olvidarse de sumarlo al script lo dejaba sin correr para siempre, en
// silencio. Acá los archivos se descubren solos.
//
//     npm test              todo (web + python)
//     npm test -- --web     solo web
//     npm test -- --python  solo python
//
// Sale con código != 0 si falla cualquier suite, que es lo que mira CI.
// ===================================================================

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const args = process.argv.slice(2);
const soloWeb = args.includes("--web");
const soloPython = args.includes("--python");
const correrWeb = !soloPython;
const correrPython = !soloWeb;

function archivosDeTest(carpeta, patron) {
  const dir = join(RAIZ, carpeta);
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((n) => patron.test(n))
    .sort()
    .map((n) => join(carpeta, n));
}

// El intérprete de Python cambia de nombre según la plataforma: en Linux
// y Mac es python3, en Windows suele ser python. Se prueba cuál responde
// en vez de asumir, para que el mismo comando ande en las dos.
function pythonDisponible() {
  for (const bin of ["python3", "python"]) {
    const r = spawnSync(bin, ["--version"], { stdio: "ignore" });
    if (!r.error && r.status === 0) return bin;
  }
  return null;
}

function correr(comando, argumentos, etiqueta) {
  console.log(`\n──────── ${etiqueta} ────────`);
  const r = spawnSync(comando, argumentos, { cwd: RAIZ, stdio: "inherit" });
  if (r.error) {
    console.error(`✗ no se pudo ejecutar: ${comando} (${r.error.message})`);
    return false;
  }
  return r.status === 0;
}

const fallaron = [];
const corridos = [];

if (correrWeb) {
  const tests = archivosDeTest("web/tests", /\.test\.js$/);
  if (tests.length === 0) {
    console.error("✗ no se encontró ningún test en web/tests/");
    fallaron.push("web (sin tests)");
  }
  for (const t of tests) {
    corridos.push(t);
    if (!correr(process.execPath, [t], t)) fallaron.push(t);
  }
}

if (correrPython) {
  const tests = archivosDeTest("app-python/tests", /^test_.*\.py$/);
  const py = tests.length ? pythonDisponible() : null;
  if (tests.length && !py) {
    // No se saltea en silencio: sin Python los tests del motor no se
    // probaron, y decir "todo verde" ahí sería mentira.
    console.error("\n✗ hay tests de Python pero no se encontró python3/python en el PATH.");
    fallaron.push("app-python (falta intérprete)");
  } else {
    for (const t of tests) {
      corridos.push(t);
      if (!correr(py, [t], t)) fallaron.push(t);
    }
  }
}

console.log("\n════════════════════════════════════════");
if (fallaron.length) {
  console.log(`✗ FALLÓ ${fallaron.length} de ${corridos.length} archivo(s) de test:`);
  for (const f of fallaron) console.log(`    · ${f}`);
  console.log("════════════════════════════════════════\n");
  process.exit(1);
}
console.log(`✓ ${corridos.length} archivo(s) de test, todo en verde`);
console.log("════════════════════════════════════════\n");
