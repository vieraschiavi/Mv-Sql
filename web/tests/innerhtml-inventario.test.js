/** Inventario clasificado de los innerHTML del código propio.
 *
 * El test de seguro.test.js prueba que la función de escape funciona. Este
 * prueba otra cosa: que TODO innerHTML del repo esté clasificado, y que no
 * aparezca uno nuevo sin clasificar. Es la diferencia entre "hoy está bien"
 * y "sigue estando bien después del próximo cambio": si alguien agrega un
 * innerHTML y no lo etiqueta, este test falla y lo obliga a decidir en qué
 * categoría cae — que es justo el momento en que se piensa si hay que
 * escapar o no.
 *
 * Las categorías están documentadas en web/assets/seguro.js:
 *   [A] VACIADO   innerHTML = "" literal
 *   [B] LITERAL   solo cadenas del I18N propio
 *   [C] LECTURA   lee, no escribe
 *   [D] ESCAPADO  dato externo, pasado por escapeHTML()
 *   [E] CRUDO     dato externo sin escapar — tiene que ser SIEMPRE cero
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const WEB = path.join(__dirname, "..");

// Solo código propio: nada de node_modules, ni carpetas de build, ni
// dependencias vendorizadas. Si algún día entra un vendor/, se excluye acá
// y se audita por versión/CVE aparte — no se cuenta en el riesgo propio.
const EXCLUIR = /node_modules|[/\\](dist|build|release|downloads|vendor)[/\\]/;

function archivosFuente(dir, acc = []) {
  for (const entrada of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entrada.name);
    if (EXCLUIR.test(p)) continue;
    if (entrada.isDirectory()) archivosFuente(p, acc);
    else if (/\.(js|html)$/.test(entrada.name)) acc.push(p);
  }
  return acc;
}

// Una ocurrencia "de código" es la que no está dentro de un comentario de
// línea. Los comentarios que EXPLICAN un innerHTML no son un innerHTML.
function ocurrencias() {
  const encontradas = [];
  for (const archivo of archivosFuente(WEB)) {
    // El propio test y seguro.js hablan de innerHTML en prosa: se saltean.
    if (/innerhtml-inventario\.test\.js$|[/\\]seguro\.js$/.test(archivo)) continue;
    const lineas = fs.readFileSync(archivo, "utf-8").split("\n");
    lineas.forEach((linea, i) => {
      if (!linea.includes("innerHTML")) return;
      if (/^\s*(\/\/|\*|<!--)/.test(linea)) return;        // línea de comentario
      encontradas.push({
        archivo: path.relative(WEB, archivo),
        linea: i + 1,
        texto: linea.trim(),
        // La etiqueta puede estar en la misma línea o en el bloque de
        // comentario inmediatamente anterior (hasta 6 líneas arriba).
        etiqueta: etiquetaDe(lineas, i),
      });
    });
  }
  return encontradas;
}

function etiquetaDe(lineas, i) {
  for (let j = i; j >= Math.max(0, i - 6); j--) {
    const m = lineas[j].match(/innerHTML \[([A-E])\]/);
    if (m) return m[1];
  }
  return null;
}

const TODAS = ocurrencias();

(async () => {
  console.log("\n== Inventario de innerHTML en código propio ==");

  await test("todas las ocurrencias están clasificadas [A]-[E]", () => {
    const sin = TODAS.filter((o) => !o.etiqueta);
    assert.deepStrictEqual(
      sin.map((o) => `${o.archivo}:${o.linea} → ${o.texto}`), [],
      "hay innerHTML sin clasificar — agregá el comentario 'innerHTML [X] ...' " +
      "según las categorías de web/assets/seguro.js");
  });

  await test("CERO ocurrencias en categoría [E] CRUDO (dato externo sin escapar)", () => {
    const crudas = TODAS.filter((o) => o.etiqueta === "E");
    assert.deepStrictEqual(crudas.map((o) => `${o.archivo}:${o.linea}`), [],
      "un innerHTML recibe dato externo sin escapar");
  });

  await test("los [A] VACIADO de verdad asignan cadena vacía y nada más", () => {
    for (const o of TODAS.filter((x) => x.etiqueta === "A")) {
      assert.ok(/innerHTML\s*=\s*(""|'')\s*;?\s*$/.test(o.texto),
        `${o.archivo}:${o.linea} dice ser [A] VACIADO pero asigna: ${o.texto}`);
    }
  });

  await test("los [C] LECTURA no tienen innerHTML del lado izquierdo de un =", () => {
    for (const o of TODAS.filter((x) => x.etiqueta === "C")) {
      assert.ok(!/\.innerHTML\s*=[^=]/.test(o.texto),
        `${o.archivo}:${o.linea} dice ser [C] LECTURA pero escribe: ${o.texto}`);
    }
  });

  await test("los [D] ESCAPADO nombran a MvSqlSeguro en la misma línea", () => {
    for (const o of TODAS.filter((x) => x.etiqueta === "D")) {
      assert.ok(/MvSqlSeguro|escapeHTML/.test(o.texto),
        `${o.archivo}:${o.linea} dice ser [D] ESCAPADO pero no llama al escape: ${o.texto}`);
    }
  });

  await test("el inventario queda impreso, para que el número no sorprenda", () => {
    const porEtiqueta = {};
    for (const o of TODAS) porEtiqueta[o.etiqueta] = (porEtiqueta[o.etiqueta] || 0) + 1;
    const resumen = ["A", "B", "C", "D", "E"]
      .map((e) => `${e}:${porEtiqueta[e] || 0}`).join("  ");
    console.log(`      ${TODAS.length} ocurrencias — ${resumen}`);
    for (const o of TODAS) console.log(`        [${o.etiqueta}] ${o.archivo}:${o.linea}`);
    assert.ok(TODAS.length > 0, "el grep no encontró nada: ¿cambió la estructura del repo?");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
