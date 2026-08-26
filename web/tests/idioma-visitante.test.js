/* © 2026 Martín Viera. Todos los derechos reservados. */

/** La landing abre en el idioma del visitante, no siempre en castellano.
 *
 * Bug que estuvo publicado: el arranque resolvía el idioma así
 *
 *     var lang=(qs&&I18N[qs])?qs:(langGuardado&&langGuardado!=='es'?langGuardado:'es');
 *
 * — sin mirar NUNCA navigator.language. O sea: el sitio tiene las tres
 * versiones (ES/EN/PT) y aun así a un visitante de Estados Unidos o de
 * Brasil le abría en castellano. Y ahí viene lo caro: Chrome le ofrece
 * traducir la página, y la traducción automática destroza justo la
 * sección de precios — "hasta 5 puestos" sale "hasta 5 postes",
 * "Profesional" sale "Professional", "Suscribirme" sale "Suscríbete".
 * Es lo último que ve el prospecto antes de poner la tarjeta.
 *
 * El comportamiento real se probó con Chromium de verdad (seis casos:
 * en-US, pt-BR, es-UY, un idioma que no hablamos, ?lang= explícito y
 * preferencia guardada). Playwright no está en las dependencias de la
 * suite del sitio, así que acá queda el guardarraíl estático que SÍ
 * corre en CI: que el código de arranque consulte el idioma del
 * navegador y respete las prioridades.
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const INDEX = path.join(__dirname, "..", "index.html");
const html = fs.readFileSync(INDEX, "utf8");

(async () => {
  console.log("\n== La landing abre en el idioma del visitante ==");

  await test("EL ARRANQUE CONSULTA EL IDIOMA DEL NAVEGADOR", () => {
    assert.ok(/navigator\.languages/.test(html) && /navigator\.language\b/.test(html),
      "index.html no mira navigator.language(s): todo visitante recibe castellano " +
      "y el navegador le ofrece traducir la página de precios");
  });

  await test("contempla los tres idiomas que el sitio realmente tiene", () => {
    // La función de detección tiene que reconocer los tres, si no el
    // visitante brasileño cae al castellano igual que antes.
    const fn = html.slice(html.indexOf("function idiomaDelNavegador"));
    assert.ok(fn.length > 0, "falta la función idiomaDelNavegador()");
    const cuerpo = fn.slice(0, fn.indexOf("}\n") + 400);
    for (const l of ["es", "en", "pt"]) {
      assert.ok(new RegExp(`'${l}'`).test(cuerpo), `no contempla '${l}'`);
    }
  });

  await test("normaliza el region tag (en-US, pt-BR) a su idioma base", () => {
    // Sin esto, navigator.language='en-US' no matchea 'en' y el
    // visitante estadounidense vuelve a caer al castellano.
    const fn = html.slice(html.indexOf("function idiomaDelNavegador"));
    assert.ok(/split\(['"]-['"]\)/.test(fn.slice(0, 600)),
      "no parte 'en-US' en su idioma base: la detección no matchearía nunca");
  });

  await test("?lang= EXPLÍCITO GANA sobre el idioma del navegador", () => {
    // Es lo que hace que un link compartido en un idioma puntual llegue
    // en ese idioma, sin importar el navegador de quien lo abre.
    const i = html.indexOf("var lang='es';");
    assert.ok(i > 0, "no se encontró la resolución de idioma de arranque");
    const bloque = html.slice(i, i + 400);
    const posQs = bloque.indexOf("qs&&I18N[qs]");
    const posNav = bloque.indexOf("idiomaDelNavegador");
    assert.ok(posQs > -1 && posNav > -1, "faltan las dos ramas de prioridad");
    assert.ok(posQs < posNav,
      "el idioma del navegador se evalúa antes que ?lang=: un link " +
      "compartido en portugués abriría en el idioma de quien lo abre");
  });

  await test("LA ELECCIÓN GUARDADA GANA sobre el navegador, aunque sea 'es'", () => {
    // La versión vieja tenía `langGuardado!=='es'`, que descartaba una
    // elección explícita de castellano. Con la detección de navegador
    // encima, eso le cambiaba el idioma al que YA había elegido
    // castellano a mano teniendo el navegador en inglés.
    const i = html.indexOf("var lang='es';");
    const bloque = html.slice(i, i + 400);
    assert.ok(!/langGuardado\s*!==\s*'es'/.test(bloque),
      "sigue descartando la preferencia guardada 'es': al visitante que " +
      "eligió castellano a mano se le vuelve a cambiar el idioma");
    const posGuardado = bloque.indexOf("langGuardado");
    const posNav = bloque.indexOf("idiomaDelNavegador");
    assert.ok(posGuardado < posNav,
      "el navegador se consulta antes que la preferencia ya guardada");
  });

  await test("un idioma que no hablamos cae al castellano, no a una página vacía", () => {
    const fn = html.slice(html.indexOf("function idiomaDelNavegador"));
    const cuerpo = fn.slice(0, 700);
    assert.ok(/return null/.test(cuerpo), "no devuelve null para un idioma desconocido");
    const i = html.indexOf("var lang='es';");
    assert.ok(/idiomaDelNavegador\(\)\s*\|\|\s*'es'/.test(html.slice(i, i + 400)),
      "no cae al castellano cuando el navegador está en un idioma que no tenemos");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
