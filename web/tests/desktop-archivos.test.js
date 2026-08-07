/** Excel/CSV como base consultable (desktop/electron/services/archivos.cjs).
 *
 * El pedido era subir Excel/CSV "sin límite de tamaño" y poder preguntarles
 * cosas como si fueran SQL. Se resolvió importando el archivo a una base
 * SQLite local en vez de cargarlo en memoria, y ese test se apoya en la
 * consecuencia: si lo importado es una base de verdad, tiene que aguantar
 * SQL de verdad — JOIN, GROUP BY, agregaciones — y no solo un SELECT *.
 *
 * Los casos son archivos rotos a propósito, porque un cliente no exporta
 * un CSV de laboratorio: exporta desde Excel en español, con punto y coma,
 * BOM, comas decimales, acentos, comillas con saltos de línea adentro y
 * encabezados repetidos. Cada uno de esos rompe un parser ingenuo, y el
 * síntoma no es un error sino datos silenciosamente mal cargados, que es
 * mucho peor: la IA contesta con números equivocados y nadie se entera.
 *
 * El caso del borde de chunk (>1 MB) es el que justifica todo el diseño:
 * el archivo se lee de a 1 MB, y tanto un carácter multibyte como una
 * fila entera pueden quedar partidos entre dos lecturas.
 */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const archivos = require(
  path.join(__dirname, "..", "..", "desktop", "electron", "services", "archivos.cjs"));

let Database;
try { Database = require(path.join(__dirname, "..", "..", "desktop", "node_modules", "better-sqlite3")); }
catch { Database = null; }

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-arch-"));
const escribir = (nombre, contenido) => {
  const p = path.join(tmp, nombre);
  fs.writeFileSync(p, contenido);
  return p;
};

/** Importa y devuelve una conexión de solo lectura a lo importado. */
async function importar(rutas) {
  const destino = path.join(tmp, `db-${Math.abs(rutas.join().length)}-${rutas[0].length}.db`);
  const r = await archivos.importar(rutas, destino);
  return { ...r, db: new Database(destino, { readonly: true }) };
}

(async () => {
  console.log("\n== Excel/CSV como base consultable ==");

  if (!Database) {
    console.log("  ! better-sqlite3 no está disponible; se corren solo los tests puros");
  }

  // ── piezas sueltas, sin tocar disco ──────────────────────────
  await test("el delimitador se detecta (Excel en español exporta con ;)", () => {
    assert.strictEqual(archivos._sniffDelimitador("id;nombre;monto"), ";");
    assert.strictEqual(archivos._sniffDelimitador("id,nombre,monto"), ",");
    assert.strictEqual(archivos._sniffDelimitador("id\tnombre\tmonto"), "\t");
    // Una coma adentro de un campo entrecomillado no vota por la coma.
    assert.strictEqual(archivos._sniffDelimitador('id;"Pérez, Juan";monto'), ";");
  });

  await test("los encabezados se vuelven nombres SQL usables", () => {
    const u = new Set();
    assert.strictEqual(archivos._identificador("Monto Vencido ($)", u, "c"), "Monto_Vencido");
    assert.strictEqual(archivos._identificador("Año", u, "c"), "Ano");
    // Repetidos: un Excel real trae dos columnas "Total". Si se pisan,
    // se pierde una sin aviso.
    assert.strictEqual(archivos._identificador("Total", u, "c"), "Total");
    assert.strictEqual(archivos._identificador("Total", u, "c"), "Total_2");
    // Empezar con número no es un identificador válido en SQL.
    assert.ok(!/^\d/.test(archivos._identificador("2024", u, "c")));
    // Un encabezado vacío no puede tumbar el CREATE TABLE.
    assert.ok(archivos._identificador("", u, "col_9").length > 0);
  });

  await test("el parser aguanta comillas, comas adentro y saltos de línea", () => {
    const filas = [];
    const p = archivos._crearParser(",", (f) => filas.push([...f]));
    p.push('a,b\n"Pérez, Juan",10\n"dice ""hola""",20\n"dos\nlíneas",30\n');
    p.fin();
    assert.deepStrictEqual(filas[1], ["Pérez, Juan", "10"], "se partió por la coma de adentro");
    assert.deepStrictEqual(filas[2], ['dice "hola"', "20"], "no desescapó las comillas dobles");
    assert.deepStrictEqual(filas[3], ["dos\nlíneas", "30"], "cortó la fila en el salto de línea interno");
  });

  await test("una fila partida entre dos lecturas no se pierde", () => {
    // Es exactamente lo que pasa cada 1 MB al leer el archivo.
    const filas = [];
    const p = archivos._crearParser(",", (f) => filas.push([...f]));
    p.push("a,b\n10,2");
    p.push("0\n30,40\n");
    p.fin();
    assert.deepStrictEqual(filas[1], ["10", "20"], "la fila cortada se corrompió");
    assert.strictEqual(filas.length, 3);
  });

  await test("las fechas se normalizan a ISO (si no, no se pueden ordenar)", () => {
    assert.strictEqual(archivos._normalizarFecha("2024-3-7"), "2024-03-07");
    assert.strictEqual(archivos._normalizarFecha("07/03/2024"), "2024-03-07");  // dd/mm en es-pt
    assert.strictEqual(archivos._normalizarFecha("no es fecha"), null);
  });

  await test("una columna toda vacía queda TEXT, no numérica", () => {
    // Si se le pone INTEGER, el primer texto que llegue después falla.
    assert.deepStrictEqual(archivos._deducirTipos([["", ""], ["", ""]], 2), ["TEXT", "TEXT"]);
  });

  if (!Database) {
    console.log(`\n  ${pasadas} pasadas · ${falladas} falladas (parcial)\n`);
    process.exit(falladas ? 1 : 0);
  }

  // ── de archivo a base consultable ────────────────────────────
  await test("un CSV de Excel en español se importa y se consulta con SQL", async () => {
    const p = escribir("ventas.csv",
      "﻿id;Cliente;Monto Vencido ($);Fecha\n" +
      '1;"Pérez, Juan";1500,50;07/03/2024\n' +
      '2;"Gómez, Ana";900,25;15/04/2024\n' +
      '3;"Pérez, Juan";800,00;02/05/2024\n');
    const { db, tablas } = await importar([p]);

    assert.strictEqual(tablas[0].tabla, "ventas");
    assert.strictEqual(tablas[0].filas, 3);

    // El BOM no se comió el nombre de la primera columna.
    const cols = db.prepare("SELECT * FROM ventas LIMIT 1").columns().map((c) => c.name);
    assert.deepStrictEqual(cols, ["id", "Cliente", "Monto_Vencido", "Fecha"]);

    // Los acentos sobrevivieron y la coma decimal se leyó como número.
    const r = db.prepare(
      "SELECT Cliente, SUM(Monto_Vencido) AS total FROM ventas GROUP BY Cliente ORDER BY total DESC").all();
    assert.strictEqual(r[0].Cliente, "Pérez, Juan");
    // 1500,50 + 800,00. Si la coma decimal se ignorara, esto daría
    // 150050 + 80000 y el total sería otro — por eso se compara el número
    // exacto y no solo el orden.
    assert.strictEqual(r[0].total, 2300.5, "la coma decimal no se interpretó como número");
    assert.strictEqual(r[1].total, 900.25);

    // Las fechas ordenan de verdad porque quedaron en ISO.
    const f = db.prepare("SELECT MIN(Fecha) AS m FROM ventas").get();
    assert.strictEqual(f.m, "2024-03-07");
    db.close();
  });

  await test("varios archivos = varias tablas, y se cruzan con JOIN", async () => {
    // Es lo que hace que esto sea SQL y no un visor de planilla.
    const a = escribir("clientes.csv", "id,nombre\n1,Ana\n2,Beto\n");
    const b = escribir("pagos.csv", "cliente_id,monto\n1,100\n1,50\n2,70\n");
    const { db } = await importar([a, b]);
    const r = db.prepare(`
      SELECT c.nombre, SUM(p.monto) AS total
      FROM clientes c JOIN pagos p ON p.cliente_id = c.id
      GROUP BY c.nombre ORDER BY total DESC`).all();
    assert.deepStrictEqual(r, [{ nombre: "Ana", total: 150 }, { nombre: "Beto", total: 70 }]);
    db.close();
  });

  await test("un archivo más grande que el buffer de lectura entra completo", async () => {
    // 1 MB es el tamaño de cada lectura: este archivo la cruza muchas
    // veces, y además mete un acento justo en cada fila para que un corte
    // en medio de un carácter multibyte se note.
    const filas = 40000;
    let txt = "id,nombre,monto\n";
    for (let i = 1; i <= filas; i++) txt += `${i},Añoración ${i},${i * 2}\n`;
    const p = escribir("grande.csv", txt);
    assert.ok(txt.length > 1 << 20, "el archivo de prueba no cruza el borde de chunk");

    const { db, tablas } = await importar([p]);
    assert.strictEqual(tablas[0].filas, filas, "se perdieron filas en el streaming");

    const c = db.prepare("SELECT COUNT(*) n, SUM(monto) s FROM grande").get();
    assert.strictEqual(c.n, filas);
    assert.strictEqual(c.s, filas * (filas + 1));  // suma de 2i = n(n+1)

    // Ningún acento se rompió al cortar entre lecturas.
    const rotos = db.prepare("SELECT COUNT(*) n FROM grande WHERE nombre NOT LIKE 'Añoración%'").get();
    assert.strictEqual(rotos.n, 0, "se corrompieron acentos en el borde de chunk");
    db.close();
  });

  await test("lo importado se abre de solo lectura", async () => {
    const p = escribir("ro.csv", "id,v\n1,10\n");
    const { db } = await importar([p]);
    assert.throws(() => db.prepare("DELETE FROM ro").run(), /readonly/i,
      "la base importada acepta escrituras");
    db.close();
  });

  await test("un CSV vacío avisa en vez de romper", async () => {
    const p = escribir("vacio.csv", "");
    await assert.rejects(() => importar([p]), /vac/i);
  });

  await test("un archivo con menos filas que la muestra igual se importa", async () => {
    // Los tipos se deducen mirando 500 filas; con 2 hay que deducirlos al
    // final igual, o la tabla no se crea nunca.
    const p = escribir("chico.csv", "id,v\n1,10\n2,20\n");
    const { db, tablas } = await importar([p]);
    assert.strictEqual(tablas[0].filas, 2);
    assert.strictEqual(db.prepare("SELECT SUM(v) s FROM chico").get().s, 30);
    db.close();
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
