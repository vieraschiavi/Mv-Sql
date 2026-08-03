/** Barrera de solo-lectura del producto de escritorio (desktop/engine.cjs).
 *
 * El desktop tenía la MISMA barrera evadible que app-python ya había cerrado:
 * assertReadOnly hacía s.includes("delete ") — con espacio — así que
 * "SELECT 1; DELETE\nFROM t" (salto de línea, no espacio) pasaba, y en SQL
 * Server, que acepta batches y no tenía readonly de sesión, borraba la tabla
 * del cliente. Este test corre la lógica real del desktop (engine.cjs es
 * CommonJS puro, no necesita Electron) y fija que los mismos payloads que
 * app-python frena, el desktop también los frene.
 *
 * Vive en web/tests/ porque es el único árbol que el runner descubre para
 * Node; requiere el módulo del desktop por path relativo.
 */
const assert = require("assert");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const { assertReadOnly } = require(
  path.join(__dirname, "..", "..", "desktop", "electron", "services", "engine.cjs"));

function frena(sql) {
  try { assertReadOnly(sql); return false; } catch { return true; }
}

(async () => {
  console.log("\n== desktop: lo que tiene que dejar pasar ==");

  await test("un SELECT y un WIT...SELECT normales", () => {
    assert.ok(!frena("SELECT id, nombre FROM clientes"));
    assert.ok(!frena("WITH t AS (SELECT * FROM ventas) SELECT * FROM t"));
  });

  await test("una columna 'update_at' o un literal con palabra reservada no molestan", () => {
    assert.ok(!frena("SELECT update_at FROM logs"));
    assert.ok(!frena("SELECT * FROM clientes WHERE nombre = 'Grant'"));
    assert.ok(!frena("SELECT ';' AS sep"));
  });

  console.log("\n== desktop: lo que tiene que frenar (los bypass del reporte) ==");

  await test("DELETE con salto de línea o tab (la evasión de la barrera vieja)", () => {
    assert.ok(frena("SELECT 1; DELETE\nFROM clientes"));
    assert.ok(frena("SELECT 1; DELETE\tFROM clientes"));
    assert.ok(frena("SELECT 1;\nDROP\nTABLE clientes"));
    assert.ok(frena("SELECT 1; TRUNCATE\nTABLE clientes"));
  });

  await test("statements encadenados con ';'", () => {
    assert.ok(frena("SELECT 1; DROP TABLE clientes"));
    assert.ok(frena("SELECT 1; ATTACH DATABASE '/tmp/x.db' AS y"));
  });

  await test("CTE modificador y DELETE escondido tras comentario", () => {
    assert.ok(frena("WITH x AS (DELETE\nFROM t RETURNING *) SELECT * FROM x"));
    assert.ok(frena("SELECT 1 /* */ ; DELETE FROM t"));
    assert.ok(frena("SELECT 1 -- \nUNION SELECT * FROM t; DROP TABLE t"));
  });

  await test("escritura/lectura al filesystem (INTO OUTFILE, load_file, OPENROWSET)", () => {
    assert.ok(frena("SELECT * FROM t INTO OUTFILE '/root/.ssh/authorized_keys'"));
    assert.ok(frena("SELECT load_file('/etc/passwd')"));
    assert.ok(frena("SELECT * INTO evil FROM clientes"));
  });

  await test("UPDATE/INSERT/DROP directos", () => {
    for (const s of ["UPDATE t SET a=1", "INSERT INTO t VALUES (1)", "DROP TABLE t",
                     "ALTER TABLE t ADD c INT", "GRANT ALL ON t TO x"]) {
      assert.ok(frena(s), `debería frenar: ${s}`);
    }
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
