/** El cliente en prueba VE cuántos días le quedan.
 *
 * El trial de Electron existía pero era invisible: el proceso principal lo
 * verificaba y bloqueaba la app al séptimo día, y el cliente no tenía
 * forma de saberlo. La app abría normal seis días y al séptimo dejaba de
 * abrir, sin ningún aviso previo.
 *
 * Es la peor forma de pedirle plata a alguien: se entera cuando ya no
 * puede trabajar, y encima parece que el programa se rompió. El producto
 * Python ya avisaba (app.py, _TXT_AVISO); esto emparejó Electron.
 *
 * Además, `licenciaEstado` estaba expuesto en el preload Y en el IPC pero
 * NADIE lo consumía: el dato viajaba hasta la interfaz y se tiraba.
 *
 * La regla de qué avisar vive en desktop/src/licencia-aviso.js, sin JSX y
 * sin React, para poder ejecutarse acá tal cual. El componente solo
 * dibuja lo que esa función decide — un primer intento metió la regla
 * adentro del JSX y hubo que transpilarlo a mano con regex para testearlo,
 * que es exactamente la clase de andamio que se rompe sola.
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
// Es ESM, así que entra por import() dinámico: un require() no lo carga.
const MODULO = path.join(RAIZ, "desktop", "src", "licencia-aviso.js");

// Los textos reales, tal como los define i18n.js.
const T = {
  trial_dias: (n) => `Prueba gratuita: te queda${n === 1 ? "" : "n"} ${n} día${n === 1 ? "" : "s"}`,
  trial_ultimo: (n) => `Tu prueba termina ${n === 1 ? "mañana" : `en ${n} días`}`,
  trial_cta: "Comprar licencia",
};

(async () => {
  console.log("\n== El cliente en prueba ve los días que le quedan ==");
  const { avisoTrial, DIAS_URGENTE } = await import(`file://${MODULO}`);

  await test("a mitad de la prueba muestra los días restantes", () => {
    const a = avisoTrial({ permitido: true, diasRestantes: 5, conLicencia: false }, T);
    assert.ok(a, "no muestra nada a mitad de la prueba: el cliente no sabe que corre un reloj");
    assert.match(a.texto, /5 días/, `no dice cuántos días quedan: "${a.texto}"`);
    assert.strictEqual(a.cta, "Comprar licencia", "no ofrece comprar");
    assert.strictEqual(a.urgente, false,
      "con 5 días ya está en tono de alarma: pierde el efecto cuando de verdad urge");
  });

  await test("EN LOS ÚLTIMOS DOS DÍAS cambia el tono", () => {
    const a = avisoTrial(
      { permitido: true, diasRestantes: DIAS_URGENTE, conLicencia: false }, T);
    assert.strictEqual(a.urgente, true,
      "faltando 2 días avisa igual que faltando 7: nadie se entera de que se termina");
    assert.match(a.texto, /termina/, `el texto no transmite el corte: "${a.texto}"`);
  });

  await test("el último día dice 'mañana', no '1 días'", () => {
    // Un producto que le cobra a una empresa no puede escribir "1 días".
    const a = avisoTrial({ permitido: true, diasRestantes: 1, conLicencia: false }, T);
    assert.match(a.texto, /mañana/, `debería decir mañana: "${a.texto}"`);
    assert.doesNotMatch(a.texto, /1 días/, "escribió '1 días'");
  });

  await test("con licencia paga NO muestra ninguna barra", () => {
    // El que pagó ya sabe que pagó; una barra permanente sería ruido.
    assert.strictEqual(
      avisoTrial({ permitido: true, diasRestantes: null, conLicencia: true }, T), null,
      "le sigue mostrando la barra de prueba a un cliente que pagó");
  });

  await test("sin respuesta del IPC todavía no muestra nada", () => {
    // El estado llega asincrónico: renderizar con null haría parpadear
    // una barra vacía en cada arranque.
    assert.strictEqual(avisoTrial(null, T), null);
  });

  await test("el umbral coincide con el del producto Python", () => {
    // Si los dos productos avisaran en momentos distintos, el mismo
    // cliente con las dos versiones vería dos promesas diferentes.
    const py = fs.readFileSync(path.join(RAIZ, "app-python", "app.py"), "utf8");
    const m = py.match(/dias_restantes"\]\s*is not None and _acceso\["dias_restantes"\]\s*<=\s*(\d+)/);
    assert.ok(m, "no se pudo leer el umbral de app.py");
    assert.strictEqual(DIAS_URGENTE, Number(m[1]),
      `Electron avisa a los ${DIAS_URGENTE} días y Python a los ${m[1]}`);
  });

  // ── el cableado, que es donde estaba el agujero ──────────────
  await test("la interfaz CONSUME licenciaEstado (estaba expuesto y sin usar)", () => {
    const app = fs.readFileSync(path.join(RAIZ, "desktop", "src", "App.jsx"), "utf8");
    assert.match(app, /licenciaEstado\(\)/,
      "App.jsx no pide el estado: el IPC existe pero el dato no llega a la pantalla");
    assert.match(app, /<AvisoLicencia/, "el aviso no está montado");

    const preload = fs.readFileSync(
      path.join(RAIZ, "desktop", "electron", "preload.cjs"), "utf8");
    assert.match(preload, /licenciaEstado/, "el preload dejó de exponerlo");
  });

  await test("los tres idiomas tienen los textos del aviso", () => {
    const i18n = fs.readFileSync(path.join(RAIZ, "desktop", "src", "i18n.js"), "utf8");
    for (const clave of ["trial_dias", "trial_ultimo", "trial_cta"]) {
      const n = (i18n.match(new RegExp(`${clave}:`, "g")) || []).length;
      assert.strictEqual(n, 3, `'${clave}' está en ${n} idiomas y tienen que ser 3 (ES/EN/PT)`);
    }
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
