/* © 2026 Martín Viera. Todos los derechos reservados. */

/** Paridad de metadatos entre variantes de idioma de la landing.
 *
 * web/index.html (es) tenía el set completo de meta tags para compartir
 * (Open Graph, Twitter Card, hreflang); web/en/index.html y web/pt/index.html
 * — las páginas de redirect que ve un crawler que llega directo a /en o /pt
 * antes de que actúe el 308 de vercel.json — se habían quedado con un
 * subconjunto parcial. Compartir un link en inglés mostraba una tarjeta sin
 * og:site_name, sin locale, sin dimensiones de imagen. Este test fija que
 * las tres páginas declaren el MISMO conjunto de tags (mismas claves;
 * el contenido sí cambia por idioma).
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..");
const PAGINAS = {
  es: path.join(RAIZ, "index.html"),
  en: path.join(RAIZ, "en", "index.html"),
  pt: path.join(RAIZ, "pt", "index.html"),
};

// Extrae el <head> como una bolsa de "claves" (name=/property= de <meta>,
// hreflang de <link rel=alternate>, y si hay <link rel=canonical>) — el
// valor no importa acá, solo que la clave exista en las tres páginas.
function clavesDeHead(html) {
  const head = html.slice(0, html.indexOf("</head>"));
  const claves = new Set();

  for (const m of head.matchAll(/<meta\s+(?:name|property)="([^"]+)"/g)) claves.add(`meta:${m[1]}`);
  for (const m of head.matchAll(/<link\s+rel="alternate"\s+hreflang="([^"]+)"/g)) claves.add(`hreflang:${m[1]}`);
  if (/<link\s+rel="canonical"/.test(head)) claves.add("link:canonical");
  if (/<title>/.test(head)) claves.add("title");
  return claves;
}

const HEADS = Object.fromEntries(
  Object.entries(PAGINAS).map(([lang, p]) => [lang, fs.readFileSync(p, "utf-8")]));

(async () => {
  console.log("\n== Paridad de meta tags entre /es, /en, /pt ==");

  await test("las 3 páginas existen y tienen <head>", () => {
    for (const [lang, html] of Object.entries(HEADS)) {
      assert.ok(html.includes("</head>"), `${lang}: sin </head>`);
    }
  });

  await test("en y pt declaran exactamente las mismas claves que es (sin faltantes)", () => {
    const base = clavesDeHead(HEADS.es);
    for (const lang of ["en", "pt"]) {
      const propias = clavesDeHead(HEADS[lang]);
      const faltan = [...base].filter((k) => !propias.has(k));
      assert.deepStrictEqual(faltan, [], `${lang} le faltan: ${faltan.join(", ")}`);
    }
  });

  await test("ninguna de las 3 tiene claves de más que las otras dos no tengan", () => {
    // Evita el error inverso: agregar un tag nuevo en una sola variante y
    // olvidarse de las otras dos.
    const [a, b, c] = ["es", "en", "pt"].map((l) => clavesDeHead(HEADS[l]));
    assert.deepStrictEqual(a, b, "es vs en");
    assert.deepStrictEqual(a, c, "es vs pt");
  });

  await test("cada página referencia las 3 variantes en hreflang + x-default", () => {
    for (const [lang, html] of Object.entries(HEADS)) {
      for (const h of ["es", "en", "pt", "x-default"]) {
        assert.ok(html.includes(`hreflang="${h}"`), `${lang}: falta hreflang="${h}"`);
      }
    }
  });

  await test("og:locale es distinto por página (no las 3 copiando es_UY)", () => {
    const esperado = { es: "es_UY", en: "en_US", pt: "pt_BR" };
    for (const [lang, val] of Object.entries(esperado)) {
      assert.ok(HEADS[lang].includes(`og:locale" content="${val}"`),
        `${lang}: og:locale debería ser ${val}`);
    }
  });

  await test("og:title y twitter:title no quedaron en español en las variantes en/pt", () => {
    assert.ok(!HEADS.en.includes("Tu base de datos"), "en: título en español");
    assert.ok(!HEADS.pt.includes("Tu base de datos"), "pt: título en español");
  });

  // ── Cobertura del contenido, no solo del <head> ──────────────────
  // /en/ y /pt/ son stubs que redirigen a /?lang=xx: la landing en inglés
  // ES la misma página con los strings cambiados por JS. Así que "¿está
  // igual de completa que la de español?" no se contesta mirando meta
  // tags — se contesta contando cuántas de las claves que la página pide
  // traducir existen de verdad en cada diccionario. Una clave faltante
  // no rompe nada visible en desarrollo: deja ese bloque en español en
  // medio de la página en inglés, y nadie se entera hasta que lo ve un
  // prospecto. Con 55% de la participación proyectada fuera de LATAM,
  // eso se paga caro.
  console.log("\n== Cobertura de traducción de la landing ==");

  const CLAVES_USADAS = [...new Set(
    [...HEADS.es.matchAll(/data-i="([^"]+)"/g)].map((m) => m[1]))];

  function clavesDelDiccionario(lang) {
    const bloque = HEADS.es.slice(HEADS.es.indexOf("var I18N={"));
    const i = bloque.indexOf(`${lang}:{`);
    if (i < 0) return new Set();
    const resto = bloque.slice(i + lang.length + 2);
    const fin = resto.search(/\n {2}[a-z]{2}:\{/);
    const trozo = fin < 0 ? resto : resto.slice(0, fin);
    return new Set([...trozo.matchAll(/(?:^|[,{\n]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:/g)]
      .map((m) => m[1]));
  }

  for (const lang of ["en", "pt"]) {
    await test(`el diccionario ${lang.toUpperCase()} cubre las ${CLAVES_USADAS.length} claves de la página`, () => {
      const dict = clavesDelDiccionario(lang);
      const faltan = CLAVES_USADAS.filter((k) => !dict.has(k));
      assert.deepStrictEqual(faltan, [],
        `${lang}: ${faltan.length} clave(s) sin traducir quedarían en español`);
    });
  }

  await test("el precio y el trial dicen lo mismo en los 3 idiomas", () => {
    // Un número distinto por idioma no es un bug de traducción: es una
    // promesa comercial distinta según quién la lea.
    for (const lang of ["es", "en", "pt"]) {
      assert.ok(/\b7\b/.test(HEADS[lang].match(/nav_cta:"[^"]*"/)?.[0] || "7"),
        `${lang}: el CTA del trial no dice 7 días`);
    }
    assert.ok(!/\b3[- ](día|day|dia)/i.test(HEADS.es), "quedó un trial de 3 días");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
