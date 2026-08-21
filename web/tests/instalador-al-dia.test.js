/* © 2026 Martín Viera. Todos los derechos reservados. */

/** El instalador .exe que sirve /api/download-instalador está al día con app-python/.
 *
 * paquete/ NO es un artefacto del CI: son archivos commiteados que
 * /api/download-instalador lee del disco y entrega gateados por licencia.
 * O sea que lo que recibe el cliente que pagó es lo que hay en el repo, no
 * lo que compiló el último Release.
 *
 * Eso ya salió mal una vez: el .exe quedó congelado 12 días mientras
 * app-python/ seguía cambiando. En el medio se corrigió el NameError que
 * mataba la app al aceptar el EULA, se sacaron los emojis y se arreglaron
 * los errores de conexión — y ninguno de esos arreglos llegaba a quien
 * bajara el instalador completo desde la web.
 *
 * No falla nada cuando pasa: el .exe se descarga, instala y abre. Solo
 * que es otro producto, más viejo. Por eso hace falta un test.
 *
 * El zip de al lado ya tiene su propio chequeo, que compara contenido
 * (zip-al-dia.test.js). Acá no se puede hacer lo mismo sin una
 * herramienta para descomprimir NSIS, así que se compara la FECHA DE
 * COMMIT: si algún archivo que viaja adentro del instalador se commiteó
 * después que el instalador, el instalador quedó viejo. Es más grosero,
 * pero no agrega dependencias y agarra justo este caso.
 */
const assert = require("assert");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const EXE = path.join(RAIZ, "paquete", "MV-SQL-NLP-Setup.exe");

/** Timestamp del último commit que tocó una ruta (0 si nunca se commiteó). */
function ultimoCommit(rutaRelativa) {
  try {
    const salida = execFileSync(
      "git", ["log", "-1", "--format=%ct", "--", rutaRelativa],
      { cwd: RAIZ, encoding: "utf8" }).trim();
    return salida ? Number(salida) : 0;
  } catch {
    return 0;
  }
}

// Lo que installer/mvsql.nsi mete adentro del .exe. No incluye tests/ ni
// __pycache__, que no viajan.
const EXTENSIONES = [".py", ".bat", ".txt", ".ico"];

/** ¿Es un clon sin historia (git clone --depth N)? */
function esShallow() {
  try {
    return execFileSync("git", ["rev-parse", "--is-shallow-repository"],
      { cwd: RAIZ, encoding: "utf8" }).trim() === "true";
  } catch {
    return false;
  }
}

(async () => {
  console.log("\n== El instalador .exe de la web está al día ==");

  await test("HAY HISTORIA DE GIT PARA COMPARAR (si no, este archivo no prueba nada)", () => {
    // Sin esto el test entero era teatro en CI. actions/checkout@v4 clona
    // shallow por defecto: el único commit no tiene padre, así que git
    // reporta TODOS los archivos como creados en él. Todas las fechas dan
    // iguales, ningún archivo puede ser "más nuevo que" el instalador, y
    // los tres tests de abajo pasaban en verde sin mirar nada.
    //
    // Medido: en un clon --depth 1 de este repo daba 3/3 verde mientras
    // que con la historia completa fallaba de verdad. Cuatro PRs pasaron
    // con CI en verde y el .exe publicado desactualizado.
    //
    // Se falla ruidosamente en vez de saltear: un chequeo que no puede
    // correr tiene que doler, no desaparecer sin que nadie lo note.
    assert.ok(!esShallow(),
      "el repo está clonado en modo shallow: las fechas de commit son todas iguales y " +
      "la comparación no prueba nada. Poné fetch-depth: 0 en el checkout de CI.");
  });

  await test("el instalador existe y no es un archivo vacío", () => {
    assert.ok(fs.existsSync(EXE), "no está paquete/MV-SQL-NLP-Setup.exe");
    const kb = fs.statSync(EXE).size / 1024;
    assert.ok(kb > 100, `pesa ${kb.toFixed(0)} KB: quedó truncado o no compiló`);
  });

  await test("NINGÚN archivo de app-python/ es más nuevo que el instalador", () => {
    const tExe = ultimoCommit("paquete/MV-SQL-NLP-Setup.exe");
    assert.ok(tExe > 0, "el instalador no está commiteado");

    const viejos = [];
    for (const f of fs.readdirSync(path.join(RAIZ, "app-python"))) {
      if (!EXTENSIONES.includes(path.extname(f))) continue;
      const t = ultimoCommit(`app-python/${f}`);
      if (t > tExe) viejos.push(`${f} (+${Math.round((t - tExe) / 86400)}d)`);
    }
    assert.deepStrictEqual(viejos, [],
      "el .exe que sirve /api/download-instalador es más viejo que el código; regeneralo con:\n" +
      "        makensis \"-DVERSION=<version>\" installer/mvsql.nsi");
  });

  await test("el zip tampoco quedó atrás del código", () => {
    // Las dos vías de descarga tienen que entregar lo mismo. Antes esto
    // se chequeaba restando las fechas de commit del .exe y del zip y
    // exigiendo menos de un día de diferencia, y esa premisa no se
    // sostiene: regenerar el zip cuando app-python no cambió da un
    // archivo BYTE A BYTE IDÉNTICO, o sea que no hay nada que commitear
    // y su fecha se queda atrás legítimamente. El caso sano hacía fallar
    // el test.
    //
    // Lo que importa de verdad es que ninguno de los dos sea más viejo
    // que el código, y eso se mide contra app-python/, no uno contra el
    // otro. Para el zip hay además un chequeo más fuerte que este, por
    // CONTENIDO, en zip-al-dia.test.js.
    const tZip = ultimoCommit("paquete/mvsql-nlp-app.zip");
    assert.ok(tZip > 0, "el zip no está commiteado");

    const viejos = [];
    for (const f of fs.readdirSync(path.join(RAIZ, "app-python"))) {
      if (!EXTENSIONES.includes(path.extname(f))) continue;
      const t = ultimoCommit(`app-python/${f}`);
      if (t > tZip) viejos.push(`${f} (+${Math.round((t - tZip) / 86400)}d)`);
    }
    assert.deepStrictEqual(viejos, [],
      "el zip que sirve /api/download es más viejo que el código; regeneralo con:\n" +
      "        python3 tools/empaquetar_zip.py");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
