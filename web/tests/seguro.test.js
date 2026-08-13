/* © 2026 Martín Viera. Todos los derechos reservados. */

/** Escape centralizado de HTML (web/assets/seguro.js).
 *
 * Hasta ahora cada página que armaba HTML a mano (owner/index.html,
 * gracias/index.html) justificaba con un comentario por qué ESE innerHTML
 * puntual era seguro. Ese comentario deja de ser cierto en silencio el día
 * que alguien edita la línea y no se da cuenta de la premisa. Este archivo
 * prueba la función que reemplaza esos comentarios por código auditable:
 * si escapeHTML() alguna vez deja pasar un payload, este test lo agarra
 * ANTES de que llegue a producción — no depende de que el próximo cambio
 * "se acuerde" de ser cuidadoso.
 */
const assert = require("assert");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const { escapeHTML, textoSeguro } = require(path.join(__dirname, "..", "assets", "seguro.js"));

// Aserción central: nada de lo que devuelve escapeHTML() puede quedar
// interpretable como una etiqueta o atributo HTML nuevo.
function sinHtmlVivo(escapado) {
  assert.ok(!/[<>]/.test(escapado), `no debería quedar < ni > crudo: ${escapado}`);
  assert.ok(!/["']/.test(escapado), `no debería quedar comilla cruda: ${escapado}`);
}

(async () => {
  console.log("\n== escapeHTML(): payloads de ataque reales ==");

  await test("neutraliza <script>", () => {
    const out = escapeHTML("<script>alert(document.cookie)</script>");
    sinHtmlVivo(out);
    assert.ok(out.includes("&lt;script&gt;"));
  });

  await test("neutraliza un <img onerror> (el mismo payload usado contra equipo.py)", () => {
    const out = escapeHTML('<img src=x onerror="alert(1)">');
    sinHtmlVivo(out);
  });

  await test("neutraliza un cierre de atributo + inyección de evento", () => {
    const out = escapeHTML('"><svg/onload=alert(1)>');
    sinHtmlVivo(out);
  });

  await test("neutraliza comillas simples usadas para escapar un atributo", () => {
    const out = escapeHTML("' onmouseover='alert(1)");
    sinHtmlVivo(out);
  });

  await test("caso real: external_reference de MercadoPago con HTML embebido", () => {
    // external_reference incluye el email que tipeó el comprador; antes de
    // pasar por celda()/textContent en owner/index.html, un valor así se
    // interpolaba directo y ejecutaba en la página que guarda el OWNER_TOKEN.
    const ref = 'profesional:credits:<img src=x onerror=alert(document.cookie)>@a.co';
    const out = escapeHTML(ref);
    sinHtmlVivo(out);
    assert.ok(out.includes("&lt;img"));
  });

  await test("& se escapa primero (si no, '&lt;' se vuelve '&amp;lt;' y listo, pero al revés duplica)", () => {
    const out = escapeHTML("Tom & Jerry <3");
    assert.strictEqual(out, "Tom &amp; Jerry &lt;3");
  });

  console.log("\n== escapeHTML(): no rompe texto normal ==");

  await test("texto plano, tildes y símbolos de plata pasan intactos salvo los 5 reservados", () => {
    assert.strictEqual(escapeHTML("Análisis de ventas — Q3 2026 (UYU $1.234,56)"),
      "Análisis de ventas — Q3 2026 (UYU $1.234,56)");
  });

  await test("null/undefined/números no revientan", () => {
    assert.strictEqual(escapeHTML(null), "");
    assert.strictEqual(escapeHTML(undefined), "");
    assert.strictEqual(escapeHTML(42), "42");
  });

  await test("aplicarlo dos veces no genera HTML nuevo (idempotente en el sentido que importa)", () => {
    const payload = "<b>x</b>";
    const una = escapeHTML(payload);
    const dos = escapeHTML(una);
    // Doble escape es más texto (&amp;lt; en vez de &lt;), pero jamás
    // reintroduce una etiqueta viva — es la propiedad que de verdad importa.
    sinHtmlVivo(dos);
  });

  console.log("\n== textoSeguro(): wrapper de textContent ==");

  await test("asigna vía textContent, nunca interpreta HTML", () => {
    const el = { textContent: "" };
    textoSeguro(el, "<b>no soy negrita</b>");
    assert.strictEqual(el.textContent, "<b>no soy negrita</b>");
  });

  await test("null/undefined se guardan como cadena vacía, no como 'null'", () => {
    const el = { textContent: "algo previo" };
    textoSeguro(el, null);
    assert.strictEqual(el.textContent, "");
  });

  await test("con elemento falsy no revienta", () => {
    assert.doesNotThrow(() => textoSeguro(null, "x"));
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
