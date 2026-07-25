/**
 * capturar.mjs — capturas del video de demo, en el idioma que se pida.
 * ==================================================================
 * Maneja la app real (la de app-python) desde el navegador y guarda
 * una captura por beat del guion. La clave: la interfaz se pone en el
 * idioma del video, así el prospecto brasileño no ve una pantalla en
 * castellano.
 *
 *   node tools/video/capturar.mjs es  /ruta/salida
 * ==================================================================
 */
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Playwright vive en web/node_modules (es donde corren los tests del sitio).
// Los módulos ESM no miran NODE_PATH, así que se resuelve a mano.
const AQUI = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
function cargarPlaywright() {
  const candidatos = [
    process.env.MVSQL_PLAYWRIGHT,
    'playwright',
    path.resolve(AQUI, '../../web/node_modules/playwright'),
    '/opt/node22/lib/node_modules/playwright',
  ].filter(Boolean);
  for (const c of candidatos) {
    try { return require(c); } catch { /* siguiente */ }
  }
  throw new Error('No se encontró playwright. Instalalo con: cd web && npm install');
}
const { chromium } = cargarPlaywright();

const IDIOMA = process.argv[2] || 'es';
const SALIDA = process.argv[3] || `/tmp/capturas_${IDIOMA}`;
// embed=true saca la barra "Deploy" y el menú de Streamlit: en cámara
// tiene que verse el producto, no el andamio de desarrollo.
const URL = (process.env.MVSQL_URL || 'http://localhost:8899') + '/?embed=true';

// Nombre del idioma tal como aparece en el desplegable de la app.
const NOMBRE_IDIOMA = { es: 'Español', en: 'English', pt: 'Português' }[IDIOMA];
// Etiquetas que cambian por idioma.
const L = {
  es: { motor: 'Motor', conectar: /Conectar/, consultar: /Consultar/, tabla: 'Tabla',
        grafico: 'Gráfico', analisis: 'Análisis', explorar: 'Explorar',
        equipo: /Equipo y permisos/, ejemplo: /Cuánto cobramos por mes/,
        fuente: 'Analizar', usuario: 'Usuario', entrar: /^Entrar$/,
        auditoria: 'Auditoría' },
  en: { motor: 'Engine', conectar: /Connect/, consultar: /Run/, tabla: 'Table',
        grafico: 'Chart', analisis: 'Analysis', explorar: 'Explore',
        equipo: /Team and permissions/, ejemplo: /Monthly collections/,
        fuente: 'Analyze', usuario: 'User', entrar: /^Sign in$/,
        auditoria: 'Audit' },
  pt: { motor: 'Motor', conectar: /Conectar/, consultar: /Consultar/, tabla: 'Tabela',
        grafico: 'Gráfico', analisis: 'Análise', explorar: 'Explorar',
        equipo: /Equipe e permiss/, ejemplo: /Quanto cobramos por m/,
        fuente: 'Analisar', usuario: 'Usuário', entrar: /^Entrar$/,
        auditoria: 'Auditoria' },
}[IDIOMA];

fs.mkdirSync(SALIDA, { recursive: true });

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
// Ventana alta y no muy ancha: el video es vertical, así la columna de
// contenido entra casi a tamaño real en la tarjeta.
const ANCHO = 1240, ALTO = 1150;
const pg = await b.newPage({ viewport: { width: ANCHO, height: ALTO }, deviceScaleFactor: 2 });
pg.on('pageerror', e => console.log('  ! error JS:', e.message));

const esperar = ms => pg.waitForTimeout(ms);
const main = () => pg.locator('[data-testid="stMain"]');

/** Centra el elemento y fotografía SOLO la columna de contenido.
 *  El video es vertical (estilo Kobra): una captura apaisada de 1440px
 *  entra tan chica que no se lee. Recortando la barra lateral el texto
 *  queda casi a tamaño real. */
async function tirar(nombre, loc) {
  if (loc) {
    // Al ras de arriba, no centrado: así el encabezado de la app (que
    // también dice "MV SQL NLP") queda fuera de cuadro. En el video la
    // marca tiene que aparecer una sola vez por frame.
    await loc.evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
    // Streamlit desplaza su propio contenedor, no la ventana.
    await pg.evaluate(() => {
      const m = document.querySelector('[data-testid="stMain"]');
      const cont = (m && m.scrollHeight > m.clientHeight) ? m : document.scrollingElement;
      cont.scrollTop -= 130;
    });
    await esperar(900);
  }
  const caja = await main().boundingBox();
  const clip = caja
    ? { x: Math.max(0, caja.x + 4), y: 0,
        width: Math.min(caja.width - 8, ANCHO - caja.x - 8), height: ALTO }
    : undefined;
  await pg.screenshot({ path: `${SALIDA}/${nombre}.png`, clip });
  console.log(`  ✓ ${nombre}.png`);
}

async function sinExcepciones(etapa) {
  const n = await pg.locator('[data-testid="stException"]').count();
  if (n) {
    const txt = await pg.locator('[data-testid="stException"]').first().innerText();
    throw new Error(`excepción en ${etapa}: ${txt.slice(0, 300)}`);
  }
}

console.log(`\n== Capturando en ${IDIOMA.toUpperCase()} ==`);
await pg.goto(URL, { waitUntil: 'load' });
await pg.locator('section[data-testid="stSidebar"]').waitFor({ timeout: 60000 });
await esperar(4000);

// 0) login: la instalación de la demo tiene control de acceso
const PIN = process.env.MVSQL_PIN || '2468';
const campoPin = pg.locator('input[type="password"]').first();
if (await campoPin.count()) {
  await campoPin.fill(PIN);
  await pg.getByRole('button', { name: /Entrar|Sign in/ }).first().click();
  await esperar(4000);
  await sinExcepciones('login');
}

// 1) idioma de la interfaz
if (IDIOMA !== 'es') {
  const sel = pg.locator('section[data-testid="stSidebar"] input').first();
  await sel.scrollIntoViewIfNeeded();
  await sel.click();
  await sel.fill(NOMBRE_IDIOMA.slice(0, 6));
  await esperar(700);
  await sel.press('Enter');
  await esperar(3500);
}
await sinExcepciones('idioma');

// 2) motor SQLite (por defecto la app arranca en modo Archivo) + conectar
const motor = pg.locator(`input[aria-label="${L.motor}"]`).first();
await motor.scrollIntoViewIfNeeded();
await motor.click();
await motor.fill('SQLite');
await esperar(600);
await motor.press('Enter');
await esperar(1500);

await pg.getByRole('button', { name: L.conectar }).first().click();
await esperar(5000);
await sinExcepciones('conexión');

// 3) la pregunta + 4) consultar
await pg.getByRole('button', { name: L.ejemplo }).first().click();
await esperar(1500);
await pg.getByRole('button', { name: L.consultar }).first().click();
await esperar(14000);
await sinExcepciones('consulta');

// La foto de la pregunta se toma recién ahora: con la página ya larga
// se puede desplazar hasta dejar el encabezado de la app fuera de cuadro
// (si no, la marca saldría dos veces en el mismo frame).
await tirar('pregunta', main().locator('input[type="text"]').first());

// SQL generado + confianza
await tirar('sql', main().locator('pre, code').first());

// 5) tabla
await pg.getByRole('tab', { name: new RegExp(L.tabla) }).first().click();
await esperar(2500);
await tirar('tabla', main().locator('[data-testid="stDataFrame"]').first());

// 6) gráfico
await pg.getByRole('tab', { name: new RegExp(L.grafico) }).first().click();
await esperar(4000);
await tirar('grafico', main().locator('.js-plotly-plot').first());

// 7) explorar: sobre una tabla entera, no sobre el resultado de 2 columnas
// (una matriz de correlación de 2x2 toda roja no muestra nada).
await pg.getByRole('tab', { name: new RegExp(L.explorar) }).first().click();
await esperar(3000);
const fuente = main().locator(`input[aria-label="${L.fuente}"]`).first();
await fuente.scrollIntoViewIfNeeded();
await fuente.click();
await fuente.fill('operaciones');
await esperar(800);
await fuente.press('Enter');
await esperar(12000);
await sinExcepciones('explorar');
await tirar('explorar', main().locator('.js-plotly-plot').first());

// 8) influencia de variables (SHAP: magnitud + dirección del efecto)
await tirar('influencia', main().locator('.js-plotly-plot').last());

// 9) auditoría: quién consultó qué (lo que un chatbot no registra)
await pg.getByRole('tab', { name: new RegExp(L.auditoria) }).first().click();
await esperar(3500);
await sinExcepciones('auditoría');
await tirar('auditoria', main().locator('[data-testid="stDataFrame"]').first());

// 10) equipo y permisos: cada uno ve solo sus tablas
const eq = pg.getByText(L.equipo).first();
await eq.scrollIntoViewIfNeeded();
await eq.click();
await esperar(2500);
// El bloque del equipo, recortado: es la prueba de que cada rol ve
// distinto, y en vertical entra tal cual.
const panel = pg.locator('section[data-testid="stSidebar"] [data-testid="stExpander"]')
                .filter({ hasText: L.equipo }).first();
const objetivo = (await panel.count()) ? panel
                 : pg.locator('section[data-testid="stSidebar"]');
await objetivo.screenshot({ path: `${SALIDA}/permisos.png` });
console.log('  ✓ permisos.png');

console.log(`Capturas en ${SALIDA}`);
await b.close();
