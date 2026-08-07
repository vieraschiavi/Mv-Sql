/** Errores de conexión del desktop (desktop/electron/services/db.cjs).
 *
 * Reportado sobre la app corriendo: con el campo del archivo vacío, apretar
 * "Conectar" contestaba
 *
 *     Error invoking remote method 'db:connect':
 *     TypeError: In-memory/temporary databases cannot be readonly
 *
 * El mensaje es correcto para el driver y no le sirve a nadie más: con la
 * ruta vacía, better-sqlite3 entiende que se le está pidiendo una base
 * temporal en memoria, y una base temporal no puede abrirse readonly. Lo
 * que el usuario tiene que hacer —elegir el .db— no aparece por ningún
 * lado, y el texto sugiere un problema del programa.
 *
 * Es el modo de falla más caro que tiene un producto que se instala solo:
 * el cliente lo ve en el primer minuto, antes de haber consultado nada, y
 * escribe "no funciona". Por eso los campos que el driver necesita se
 * validan ANTES de llamarlo, y por eso se fija acá.
 *
 * Se prueban los cuatro motores porque el problema no es de SQLite: es de
 * dejar que el driver hable primero. Un servidor vacío en SQL Server da
 * un timeout de 30 segundos y después un error de red igual de opaco.
 */
const assert = require("assert");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const db = require(
  path.join(__dirname, "..", "..", "desktop", "electron", "services", "db.cjs"));

async function error(cfg) {
  try {
    await db.connect(cfg);
    return null;
  } catch (e) {
    return e.message;
  }
}

(async () => {
  console.log("\n== Conexión: qué se le dice al usuario cuando falta un dato ==");

  await test("SQLite sin archivo: dice qué hacer, no qué le pasó al driver", async () => {
    const msg = await error({ motor: "sqlite", ruta: "" });
    assert.ok(msg, "no falló: iba a llegar al driver con la ruta vacía");
    assert.ok(!/in-memory|readonly|TypeError/i.test(msg),
      `volvió el error crudo del driver: ${msg}`);
    assert.ok(/\.db/.test(msg), `no menciona el archivo que falta: ${msg}`);
  });

  await test("una ruta con espacios cuenta como vacía", async () => {
    // Un placeholder copiado, o un espacio de más, no debería llegar al driver.
    assert.ok(await error({ motor: "sqlite", ruta: "   " }));
  });

  await test("los motores de servidor piden servidor y base", async () => {
    for (const motor of ["sqlserver", "mysql", "postgres"]) {
      const sinServidor = await error({ motor, base: "ventas" });
      assert.ok(/servidor/i.test(sinServidor || ""),
        `${motor}: no pide el servidor (${sinServidor})`);

      const sinBase = await error({ motor, servidor: "10.0.0.1" });
      assert.ok(/base/i.test(sinBase || ""),
        `${motor}: no pide el nombre de la base (${sinBase})`);
    }
  });

  await test("un motor desconocido no se cae con un error interno", async () => {
    const msg = await error({ motor: "oracle" });
    assert.ok(/oracle/i.test(msg || ""), `no nombra el motor pedido: ${msg}`);
  });

  await test("la contraseña vacía SÍ se acepta (hay bases sin password)", async () => {
    // Validar de más también rompe: una base local de desarrollo o una
    // integrada de Windows puede no llevar contraseña, y exigirla dejaría
    // afuera a un cliente que sí puede conectar.
    const msg = await error({ motor: "mysql", servidor: "10.0.0.1", base: "v", password: "" });
    assert.ok(!/password|contrase/i.test(msg || ""),
      `se está exigiendo contraseña de más: ${msg}`);
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
