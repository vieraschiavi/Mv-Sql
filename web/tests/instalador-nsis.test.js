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
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

let pasadas = 0, falladas = 0, omitidas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const NSH = path.join(RAIZ, "desktop", "build", "installer.nsh");
const YML = path.join(RAIZ, "desktop", "electron-builder.yml");

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

  // ==========================================================================
  // El gate de verdad: compilarlo con makensis
  // ==========================================================================
  // Todo lo de arriba mira el texto del archivo. Eso alcanza para la regla
  // que ya se rompió una vez (el !include faltante), pero no para lo que
  // venga después. Acá se lo compila de verdad, en el mismo orden en que lo
  // mete electron-builder: el .nsh PRIMERO, sin ningún !include previo que
  // le regale contexto. Si no compila así, no compila en el release.
  //
  // Y se compilan LAS DOS PASADAS, con -WX, porque electron-builder corre
  // makensis dos veces sobre el mismo installer.nsi:
  //
  //   1. el instalador   → customInit SÍ se inserta
  //   2. el desinstalador → con BUILD_UNINSTALLER definido, y ahí
  //      installer.nsi NO inserta customInit
  //
  // Este archivo antes simulaba solo la primera, que es justo la que
  // funcionaba, y por eso dejó pasar el bug que volteó el build de la
  // 1.0.9: una Function definida y sin referencia en la pasada 2 dispara
  // "warning 6010 ... not referenced", y con -WX (que es como lo corre
  // electron-builder) ese warning es un error. Simular una sola pasada era
  // otra versión del mismo error de método que ya cuenta el encabezado.
  console.log("\n== installer.nsh compila con makensis (las dos pasadas) ==");

  const hayMakensis =
    spawnSync("makensis", ["-VERSION"], { encoding: "utf8" }).status === 0;

  if (!hayMakensis) {
    // En CI esto es un error: el workflow instala nsis a propósito, así que
    // si falta es que alguien sacó ese paso y el gate quedó apagado sin
    // que nadie lo note. En una máquina de desarrollo sin nsis, se omite
    // — pero se dice, y NO cuenta como pasada.
    await test("makensis está disponible (CI lo instala en tests.yml)", () => {
      assert.ok(!process.env.CI,
        "no hay makensis en el PATH y esto es CI: revisá el paso " +
        "'Instalar NSIS' de .github/workflows/tests.yml");
    });
    if (!process.env.CI) {
      console.log("  – omitido: no hay makensis en esta máquina " +
                  "(instalalo con: sudo apt-get install nsis)");
      omitidas++;
    }
  } else {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "mvsql-nsis-"));
    const esc = (x) => x.replace(/\\/g, "\\\\");

    /** Un arnés por pasada. Los defines y la Var son EXACTAMENTE los que
     *  installer.nsh consume del contexto de electron-builder, y nada más:
     *  si mañana usa uno nuevo sin protegerlo con !ifdef, acá revienta.
     *  perUserInstallationFolder se escribe además de declararse porque en
     *  el instalador real la escribe multiUser.nsh; sin eso NSIS avisaría
     *  que "desperdicia memoria" y el arnés inventaría un warning propio. */
    function armar(nombre, { desinstalador }) {
      const guion = [
        ...(desinstalador ? ["!define BUILD_UNINSTALLER"] : []),
        '!define VERSION "9.9.9"',
        '!define APP_64_UNPACKED_SIZE "358400"',
        "Var perUserInstallationFolder",
        `!include "${esc(NSH)}"`,
        `OutFile "${esc(path.join(dir, `${nombre}.exe`))}"`,
        "Function .onInit",
        '  StrCpy $perUserInstallationFolder ""',
        // La pasada del desinstalador NO inserta customInit: así lo hace
        // installer.nsi cuando BUILD_UNINSTALLER está definido.
        ...(desinstalador ? [] : ["  !insertmacro customInit"]),
        "FunctionEnd",
        "Section",
        "SectionEnd",
      ].join("\n");
      const nsi = path.join(dir, `${nombre}.nsi`);
      fs.writeFileSync(nsi, guion, "utf8");
      // -WX: warnings como errores, igual que electron-builder.
      const r = spawnSync("makensis", ["-WX", nsi], { encoding: "utf8" });
      return { nsi, guion, r, salida: `${r.stdout || ""}${r.stderr || ""}` };
    }

    const inst = armar("instalador", { desinstalador: false });
    const desinst = armar("desinstalador", { desinstalador: true });
    const { nsi, guion, r, salida } = inst;

    await test("PASADA 1 (instalador): compila incluido de primero y sin warnings", () => {
      assert.strictEqual(r.status, 0,
        `makensis -WX salió con ${r.status}:\n${salida.split("\n").slice(-25).join("\n")}`);
    });

    await test("PASADA 2 (desinstalador): compila con BUILD_UNINSTALLER y sin customInit", () => {
      // Esta es la que volteó el build de la 1.0.9. Todo lo que installer.nsh
      // defina y solo use desde customInit tiene que estar detrás de
      // !ifndef BUILD_UNINSTALLER, o NSIS avisa que no se referencia y -WX
      // convierte ese aviso en un release fallido.
      assert.strictEqual(desinst.r.status, 0,
        `makensis -WX salió con ${desinst.r.status} en la pasada del desinstalador.\n` +
        "Si dice 'not referenced', poné eso adentro de !ifndef BUILD_UNINSTALLER:\n" +
        desinst.salida.split("\n").filter((l) => /warning|error/i.test(l)).join("\n"));
    });

    await test("no deja warnings propios (los de NSIS también rompen releases)", () => {
      // El único warning esperable es del arnés, no del .nsh: la Var
      // perUserInstallationFolder se declara acá y installer.nsh la lee
      // pero nadie la escribe, así que NSIS avisa que "desperdicia memoria".
      const warnings = salida.split("\n")
        .filter((l) => /^\s*(warning|!warning)/i.test(l))
        .filter((l) => !l.includes("perUserInstallationFolder"));
      assert.deepStrictEqual(warnings, [],
        `warnings inesperados:\n${warnings.join("\n")}`);
    });

    await test("el mensaje de espacio queda en el .exe en los TRES idiomas", () => {
      // Se lee el binario compilado, no el fuente: es la única forma de
      // saber que los acentos sobreviven al pasaje a UTF-16 del instalador
      // Unicode. Un mensaje con "Nao ha espaco" pasaría cualquier chequeo
      // sobre el .nsh y quedaría feo en la pantalla del cliente.
      // Sin comprimir: si no, las cadenas viajan adentro del bloque LZMA y
      // no se pueden buscar en el binario.
      const sinComp = path.join(dir, "sincomp.nsi");
      fs.writeFileSync(sinComp, `SetCompress off\n${guion}`, "utf8");
      const c = spawnSync("makensis", ["-WX", sinComp], { encoding: "utf8" });
      assert.strictEqual(c.status, 0, "no compiló la variante sin comprimir");

      const exe = fs.readFileSync(path.join(dir, "instalador.exe"));
      for (const [idioma, frase] of Object.entries({
        es: "No hay espacio suficiente en la unidad",
        en: "Not enough free space on drive",
        pt: "Não há espaço suficiente na unidade",
      })) {
        assert.ok(exe.includes(Buffer.from(frase, "utf16le")),
          `falta el aviso en ${idioma}: "${frase}"`);
      }
    });

    await test("el chequeo de espacio está ENGANCHADO a customInit, no solo escrito", () => {
      // Sin esto el archivo pasaría todos los tests de arriba con la macro
      // MvsqlChequearEspacio definida y jamás insertada: la Function del
      // aviso se compila igual y sus tres mensajes quedan igual dentro del
      // .exe, así que el test de los idiomas daría verde con el chequeo
      // desconectado. Lo único que distingue "existe" de "corre" es que el
      // cuerpo de la macro aparezca en la expansión de customInit.
      const pp = spawnSync("makensis", ["-PPO", nsi], { encoding: "utf8" });
      assert.strictEqual(pp.status, 0, "no se pudo preprocesar el arnés");
      assert.ok(pp.stdout.includes("$TEMP"),
        "customInit se expande sin tocar $TEMP: el chequeo de la carpeta " +
        "temporal quedó definido pero nunca insertado");
    });

    await test("el aviso nombra el .zip con la versión real, no un placeholder", () => {
      const exe = fs.readFileSync(path.join(dir, "instalador.exe"));
      assert.ok(exe.includes(Buffer.from("MV-SQL-NLP-9.9.9.zip", "utf16le")),
        "el ${VERSION} del mensaje no se expandió: el cliente vería el literal");
    });
  }

  // ==========================================================================
  // La otra mitad del arreglo vive en electron-builder.yml
  // ==========================================================================
  console.log("\n== la carpeta temporal no tiene que aguantar el doble ==");

  const yml = fs.readFileSync(YML, "utf8");
  // Sin comentarios: "useZip" aparece cinco veces en la explicación de por
  // qué está, y un indexOf sobre el archivo entero daría verde aunque la
  // opción no estuviera puesta. Ya pasó dos veces en este repo.
  const ymlSinComentarios = yml.split("\n")
    .filter((l) => !/^\s*#/.test(l)).join("\n");

  await test("useZip: el paquete se descomprime directo a la carpeta de instalación", () => {
    assert.match(ymlSinComentarios, /^\s*useZip:\s*true\s*$/m,
      "sin useZip, NSIS descomprime en $PLUGINSDIR\\7z-out (la carpeta " +
      "temporal, en C:) y recién después copia: pide ~440 MB en la unidad " +
      "del perfil aunque instales en otra");
  });

  await test("differentialPackage: false, si no useZip se ignora en silencio", () => {
    assert.match(ymlSinComentarios, /^\s*differentialPackage:\s*false\s*$/m,
      "app-builder-lib solo respeta useZip si !isBuildDifferentialAware " +
      "(NsisTarget.js: `!isBuildDifferentialAware && options.useZip`). Con " +
      "differentialPackage sin poner en false, useZip queda decorativo.");
  });

  await test("nadie usa electron-updater (que es lo que differentialPackage servía)", () => {
    // Si algún día se agrega autoactualización, el .blockmap vuelve a hacer
    // falta y hay que reconsiderar el cambio de arriba en vez de descubrir
    // que las actualizaciones bajan el instalador entero cada vez.
    const pkg = fs.readFileSync(path.join(RAIZ, "desktop", "package.json"), "utf8");
    assert.ok(!/electron-updater/.test(pkg),
      "apareció electron-updater: differentialPackage: false ahora tiene " +
      "costo real (se pierden las actualizaciones diferenciales)");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas` +
              `${omitidas ? ` · ${omitidas} omitidas` : ""}\n`);
  process.exit(falladas ? 1 : 0);
})();
