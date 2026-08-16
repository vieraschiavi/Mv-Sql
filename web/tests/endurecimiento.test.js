/* © 2026 Martín Viera. Todos los derechos reservados. */

/** Tres agujeros encontrados en una auditoría end-to-end, y sus candados.
 *
 * Ninguno rompía nada de forma visible: la app abría, la web cargaba, CI
 * daba verde. Por eso hacen falta tests — un bug que no se nota es el que
 * se queda.
 *
 *   1. COSTO SIN TECHO en /api/ai-proxy. El contador de créditos limita
 *      cuántas llamadas, no cuánto cuesta cada una: max_tokens y el largo
 *      del prompt venían del cliente sin límite. Una licencia de créditos
 *      podía gastar, contra la tarjeta del dueño, un múltiplo enorme de
 *      lo que se cobró por ese paquete — y quedaba registrado como uso
 *      normal.
 *
 *   2. LO EXTERNO SE ABRÍA ADENTRO DE LA APP. Sin setWindowOpenHandler,
 *      el <a target="_blank"> del aviso de prueba —el botón "Comprar
 *      licencia", el único camino de venta— abría una segunda ventana de
 *      Electron con mvsqlnlp.com adentro. Una ventana de Electron no
 *      tiene barra de direcciones: el cliente no ve el dominio, no tiene
 *      su gestor de contraseñas ni sus tarjetas guardadas. Justo al pagar.
 *      Verificado corriendo la app real bajo xvfb: antes 2 ventanas,
 *      después 1 y el link al navegador del sistema.
 *
 *   3. LA BARRA SUPERIOR DESBORDABA EN CELULAR. Los items de un flex
 *      arrancan con min-width:auto, así que se niegan a encoger por
 *      debajo de su contenido y desbordan. A 360px eso daba 28px de
 *      scroll horizontal en la página que vende el producto; a 320px,
 *      68px.
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
// Secuencial y con await: varios de estos tests pisan global.fetch y el
// require.cache de @vercel/kv, así que corriendo en paralelo se roban el
// doble entre ellos y fallan por su propia culpa, no por el código.
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const leer = (...p) => fs.readFileSync(path.join(RAIZ, ...p), "utf8");

/** Devuelve el cuerpo de un bloque @media, contando llaves. */
function bloqueMedia(css, inicio) {
  const i = css.indexOf(inicio);
  if (i < 0) return null;
  let nivel = 0;
  for (let j = i + inicio.length - 1; j < css.length; j++) {
    if (css[j] === "{") nivel++;
    else if (css[j] === "}" && --nivel === 0) return css.slice(i, j + 1);
  }
  return null;
}

console.log("\n== Endurecimiento: costo, ventanas externas y overflow ==");

// ── 1. Techo de costo en el proxy de IA ──────────────────────────
(async () => {
  process.env.LICENSE_SECRET = process.env.LICENSE_SECRET || "secreto-de-prueba";
  const API = path.join(RAIZ, "web", "api");
  const { issueLicense } = require(path.join(API, "_license.js"));

  /** Corre el endpoint con KV y Anthropic falsos, y devuelve lo que se le pidió a la IA. */
  async function llamar(cuerpo) {
    // KV en memoria: sin esto el endpoint hace fail-closed con 503 y no
    // se llega a probar nada del costo.
    const contador = new Map();
    const rutaKv = require.resolve("@vercel/kv");
    const previoKv = require.cache[rutaKv];
    require.cache[rutaKv] = {
      id: rutaKv, filename: rutaKv, loaded: true,
      exports: {
        kv: {
          incr: async (k) => { contador.set(k, (contador.get(k) || 0) + 1); return contador.get(k); },
          decr: async (k) => { contador.set(k, (contador.get(k) || 0) - 1); return contador.get(k); },
        },
      },
    };
    process.env.KV_REST_API_URL = "https://kv-de-prueba";
    process.env.ANTHROPIC_API_KEY = "sk-ant-de-prueba";

    let pedido = null;
    const previoFetch = global.fetch;
    global.fetch = async (url, opciones) => {
      pedido = JSON.parse(opciones.body);
      return { ok: true, status: 200, json: async () => ({ content: [{ text: "ok" }] }) };
    };

    const rutaProxy = path.join(API, "ai-proxy.js");
    delete require.cache[require.resolve(rutaProxy)];
    const proxy = require(rutaProxy);

    let estado = null, salida = null;
    const res = {
      setHeader() {},
      status(c) { estado = c; return this; },
      json(b) { salida = b; return this; },
      send(b) { salida = b; return this; },
    };
    try {
      await proxy({ method: "POST", headers: { host: "x" }, body: cuerpo, query: {} }, res);
    } finally {
      global.fetch = previoFetch;
      if (previoKv) require.cache[rutaKv] = previoKv; else delete require.cache[rutaKv];
    }
    return { estado, salida, pedido };
  }

  const tokenCreditos = issueLicense({
    email: "x@y.com", plan: "profesional", mode: "credits", paymentId: "123456789" });

  await test("UN max_tokens ENORME SE RECORTA (no se le pasa crudo a la IA)", async () => {
    const { pedido } = await llamar({ token: tokenCreditos, user: "hola", max_tokens: 200000 });
    assert.ok(pedido, "no se llegó a llamar a la IA");
    assert.ok(pedido.max_tokens <= 4000,
      `se le pidió a la IA ${pedido.max_tokens} tokens: un crédito puede costar cualquier cosa`);
  });

  await test("un max_tokens normal se respeta tal cual", async () => {
    const { pedido } = await llamar({ token: tokenCreditos, user: "hola", max_tokens: 1500 });
    assert.strictEqual(pedido.max_tokens, 1500);
  });

  await test("sin max_tokens usa el default de siempre", async () => {
    const { pedido } = await llamar({ token: tokenCreditos, user: "hola" });
    assert.strictEqual(pedido.max_tokens, 1500);
  });

  await test("un max_tokens basura no rompe ni se cuela", async () => {
    for (const basura of ["muchos", -5, 0, NaN, null]) {
      const { pedido, estado } = await llamar({ token: tokenCreditos, user: "hola", max_tokens: basura });
      assert.strictEqual(estado, 200, `max_tokens=${basura} devolvió ${estado}`);
      assert.ok(pedido.max_tokens >= 1 && pedido.max_tokens <= 4000,
        `max_tokens=${basura} produjo ${pedido.max_tokens}`);
    }
  });

  await test("UN PROMPT DESMEDIDO SE RECHAZA ANTES de gastar un crédito", async () => {
    const { estado, pedido } = await llamar({ token: tokenCreditos, user: "A".repeat(50000) });
    assert.strictEqual(estado, 413, `devolvió ${estado} en vez de 413`);
    assert.strictEqual(pedido, null, "llamó a la IA igual: el gasto ya se hizo");
  });

  await test("un prompt de tamaño real sigue pasando", async () => {
    // El producto manda esquema (nombres de tablas/columnas), no datos.
    const { estado } = await llamar({ token: tokenCreditos, user: "A".repeat(8000) });
    assert.strictEqual(estado, 200, `un prompt legítimo fue rechazado con ${estado}`);
  });

// ── 2. Nada externo se abre adentro de la app ────────────────────
await test("EL PROCESO PRINCIPAL DE ELECTRON manda lo externo al navegador", () => {
  const main = leer("desktop", "electron", "main.cjs");
  // \b al principio para que renombrar el método (prefijarlo, comentarlo
  // a medias) no siga matcheando por substring: la primera versión de
  // este test pasaba con la llamada rota justamente por eso.
  assert.match(main, /\bwin\.webContents\.setWindowOpenHandler\s*\(/,
    "no se registra setWindowOpenHandler sobre la ventana: un target=\"_blank\" abre " +
    "una ventana de Electron sin barra de direcciones — y el único link del producto " +
    "es el de comprar");
  assert.match(main, /action:\s*["']deny["']/,
    "el handler existe pero no deniega la ventana interna");
  assert.match(main, /\bwin\.webContents\.on\(\s*["']will-navigate["']/,
    "falta el guard de will-navigate: la ventana de la app puede irse a otro sitio en el lugar");
  assert.match(main, /preventDefault\(\)/,
    "will-navigate está enganchado pero no frena la navegación");
  assert.match(main, /\^https:\\\/\\\//,
    "openExternal se llama sin restringir a https: file: y otros esquemas los abre el sistema operativo");
});

await test("el aviso de prueba sigue mandando a la página de precios", () => {
  // Si el link se rompe, el producto se queda sin camino de venta y el
  // test de arriba (que solo mira main.cjs) no se entera.
  const aviso = leer("desktop", "src", "licencia-aviso.js");
  assert.match(aviso, /https:\/\/mvsqlnlp\.com/, "el aviso ya no apunta a la web");
});

// ── 3. La barra superior no desborda en celular ──────────────────
await test("LA BARRA SUPERIOR PUEDE ENCOGER EN PANTALLA CHICA (min-width:0)", () => {
  const html = leer("web", "index.html");
  const bloque = bloqueMedia(html, "@media(max-width:620px){");
  assert.ok(bloque, "desapareció el media query de pantallas chicas");
  // Se exige la regla sobre EL contenedor que desbordaba (nav .right),
  // no un min-width:0 cualquiera del bloque: la primera versión de este
  // test seguía en verde con la regla borrada, porque matcheaba el
  // min-width:0 de .pais-sel que quedaba más abajo.
  assert.match(bloque, /nav\s+\.right\{[^}]*min-width:\s*0/,
    "sin min-width:0 en 'nav .right' los items del flex se niegan a encoger por " +
    "debajo de su contenido y devuelven el scroll horizontal a 360px");
  assert.match(bloque, /nav\s+\.wrap\{[^}]*flex-wrap:\s*wrap/,
    "sin wrap en la barra, el contenido se empuja fuera de la pantalla en vez de " +
    "pasar a dos líneas");
});

await test("la landing tiene salto al contenido y landmark main, en los 3 idiomas", () => {
  // WCAG 2.4.1: sin salto al contenido, navegar con teclado o con lector
  // de pantalla obliga a recorrer toda la barra (idiomas, país, menú)
  // antes de llegar a nada, en cada carga de página.
  const html = leer("web", "index.html");
  assert.match(html, /<a class="skip" href="#contenido"/, "falta el salto al contenido");
  assert.match(html, /<main id="contenido">/, "falta el landmark <main> al que salta");
  assert.match(html, /<\/main>/, "el <main> quedó sin cerrar");
  assert.match(html, /\.skip\{[^}]*position:absolute/,
    "el salto no está oculto: sin eso aparece siempre arriba de todo");
  assert.match(html, /\.skip:focus\{/,
    "el salto está oculto pero nunca se muestra al enfocarlo con Tab");
  assert.match(html, /skip:"Pular/, "el salto al contenido no está traducido a pt");
  assert.match(html, /skip:"Skip/, "el salto al contenido no está traducido a en");
});

await test("la landing declara el viewport (sin esto no hay responsive que valga)", () => {
  const html = leer("web", "index.html");
  assert.match(html, /name="viewport"[^>]*width=device-width/,
    "falta el meta viewport: el celular renderiza a 980px y escala todo");
});

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
