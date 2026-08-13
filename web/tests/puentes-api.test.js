/* © 2026 Martín Viera. Todos los derechos reservados. */

/** Cada endpoint tiene su puente en la raíz, o en producción es un 404.
 *
 * La implementación de la API vive en web/api/, pero el proyecto de
 * Vercel publica desde la RAÍZ del repositorio, y Vercel busca las
 * funciones serverless en api/ de la raíz y en ningún otro lado. Por eso
 * hay una carpeta api/ con un archivo por endpoint que no hace más que
 * reexportar el de web/api/.
 *
 * Es exactamente el tipo de paso que se olvida: el endpoint nuevo queda
 * completo, testeado y en verde, y en producción devuelve 404 sin que
 * nada lo avise. Pasó con /api/renovar-licencia — se escribió el
 * endpoint, se escribieron sus tests, se cablearon los dos clientes, y
 * la ruta no existía. El síntoma es peor que un error: el cliente que
 * paga ve la app comportarse como si su suscripción estuviera cancelada.
 *
 * Este archivo vuelve imposible el olvido: agregar un endpoint sin su
 * puente rompe la suite.
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
function test(n, fn) {
  try { fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const API_REAL = path.join(RAIZ, "web", "api");
const API_RAIZ = path.join(RAIZ, "api");

// Los que empiezan con "_" son módulos compartidos, no rutas: no llevan
// puente porque nadie los pide por URL.
const endpoints = fs.readdirSync(API_REAL)
  .filter((f) => f.endsWith(".js") && !f.startsWith("_"))
  .sort();

console.log("\n== Los endpoints existen de verdad en producción ==");

test("hay endpoints que revisar (si no, este test no prueba nada)", () => {
  assert.ok(endpoints.length >= 5, `solo se encontraron ${endpoints.length} endpoints`);
});

for (const archivo of endpoints) {
  test(`/api/${archivo.replace(/\.js$/, "")} tiene su puente en la raíz`, () => {
    const puente = path.join(API_RAIZ, archivo);
    assert.ok(fs.existsSync(puente),
      `falta api/${archivo}: en producción esa ruta devuelve 404 aunque el endpoint esté perfecto`);
    const src = fs.readFileSync(puente, "utf8");
    assert.match(src, new RegExp(`require\\("\\.\\./web/api/${archivo.replace(".", "\\.")}"\\)`),
      `api/${archivo} no reexporta el de web/api: la lógica se duplicó y va a divergir`);
  });
}

test("los puentes CARGAN (un require roto es un 500 en cada pedido)", () => {
  // Un puente puede existir y aun así reventar al cargar, si el módulo
  // real requiere algo que no está donde el puente lo busca. Eso en
  // Vercel es un 500 en frío, no un error de build.
  process.env.LICENSE_SECRET = process.env.LICENSE_SECRET || "secreto-de-prueba";
  process.env.MP_ACCESS_TOKEN = process.env.MP_ACCESS_TOKEN || "TEST-mp";
  for (const archivo of endpoints) {
    const cargado = require(path.join(API_RAIZ, archivo));
    assert.strictEqual(typeof cargado, "function",
      `api/${archivo} no exporta un handler: Vercel no la va a poder invocar`);
  }
});

test("no quedan puentes hacia endpoints que ya no existen", () => {
  // Un puente huérfano es una ruta que revienta al invocarse.
  const huerfanos = fs.readdirSync(API_RAIZ)
    .filter((f) => f.endsWith(".js") && !endpoints.includes(f));
  assert.deepStrictEqual(huerfanos, [],
    `sobran puentes sin endpoint detrás: ${huerfanos.join(", ")}`);
});

console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
process.exit(falladas ? 1 : 0);
