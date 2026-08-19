/* © 2026 Martín Viera. Todos los derechos reservados. */

/** desktop/build/installer.nsh trae sus propias dependencias de NSIS.
 *
 * Este archivo existe por un release roto de verdad (v1.0.3). El
 * instalador de Electron fallaba al compilar con:
 *
 *   Invalid command: "${DriveSpace}"
 *   !include: error in script: "...\build\installer.nsh" on line 103
 *
 * La causa es una asimetría de NSIS fácil de no ver: lo que está adentro
 * de un !macro NO se expande al momento del !include (queda guardado tal
 * cual y se resuelve al insertarlo), pero una Function se compila EN EL
 * ACTO. Por eso el ${DriveSpace} de adentro de customInit pasaba sin
 * chistar y el de la Function de abajo explotaba: cuando electron-builder
 * mete ese archivo, todavía no incluyó FileFunc.nsh.
 *
 * Lo peor no fue el bug sino cómo se coló: se había "verificado" con un
 * stub de makensis que incluía FileFunc.nsh por su cuenta antes de meter
 * el .nsh. O sea que el stub le daba a installer.nsh un contexto que
 * electron-builder no le da, y tapaba exactamente el problema que tenía
 * que encontrar. Un chequeo que crea las condiciones de su propio éxito
 * no está verificando nada.
 *
 * De ahí las dos reglas de abajo: el archivo tiene que declarar lo que
 * usa, y no puede depender de que alguien más lo haya incluido antes.
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
const NSH = path.join(RAIZ, "desktop", "build", "installer.nsh");

/** Headers de NSIS que definen cada macro ${...} que usamos. */
const DUENO = {
  "FileFunc.nsh": ["GetRoot", "DriveSpace", "GetDrives"],
  "LogicLib.nsh": ["If", "EndIf"],
};

(async () => {
  console.log("\n== installer.nsh declara lo que usa ==");

  const nsh = fs.existsSync(NSH) ? fs.readFileSync(NSH, "utf8") : "";

  await test("el archivo existe (si no, no hay nada que verificar)", () => {
    assert.ok(nsh.length > 0, "falta desktop/build/installer.nsh");
  });

  await test("está enganchado en electron-builder.yml (si no, no se compila nunca)", () => {
    const yml = fs.readFileSync(
      path.join(RAIZ, "desktop", "electron-builder.yml"), "utf8");
    assert.match(yml, /^\s*include:\s*build\/installer\.nsh\s*$/m,
      "electron-builder.yml no tiene 'include: build/installer.nsh' en el bloque nsis");
  });

  await test("USA UNA FUNCTION: por eso los ${...} se expanden al incluir, no al insertar", () => {
    // Si algún día se reescribe todo adentro del !macro y no queda
    // ninguna Function, la exigencia de abajo deja de ser necesaria —
    // y este test tiene que dejar de mentir sobre por qué existe.
    assert.match(nsh, /^\s*Function\s+\w+/m,
      "ya no hay ninguna Function: revisá si sigue haciendo falta el !include explícito");
  });

  for (const [header, macros] of Object.entries(DUENO)) {
    const usadas = macros.filter((m) =>
      new RegExp(`\\$\\{${m}\\}`).test(nsh));
    if (usadas.length === 0) continue;

    await test(`incluye ${header} (usa ${usadas.map((m) => "${" + m + "}").join(", ")})`, () => {
      assert.match(nsh, new RegExp(`^\\s*!include\\s+"${header.replace(".", "\\.")}"`, "m"),
        `usa ${usadas.join("/")} de ${header} pero nunca lo incluye. ` +
        `electron-builder NO garantiza haberlo incluido antes: las Function ` +
        `se compilan en el momento del !include y revientan con ` +
        `'Invalid command'. Agregá !include "${header}".`);
    });
  }

  await test("el !include va ANTES de la primera Function que lo necesita", () => {
    const iFileFunc = nsh.indexOf('!include "FileFunc.nsh"');
    const iFunction = nsh.search(/^\s*Function\s+\w+/m);
    assert.ok(iFileFunc >= 0, "no está el !include de FileFunc.nsh");
    assert.ok(iFunction >= 0, "no hay ninguna Function");
    assert.ok(iFileFunc < iFunction,
      "el !include de FileFunc.nsh está DESPUÉS de la Function que usa sus macros: " +
      "NSIS compila la Function en el acto, así que llega tarde");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
