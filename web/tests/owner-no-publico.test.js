/* © 2026 Martín Viera. Todos los derechos reservados. */

/** El instalador del propietario nunca puede terminar en un lugar público.
 *
 * Ese .exe abre sin trial y con una licencia que vence en 2099. Si aparece
 * como asset de un Release de un repositorio público, cualquiera se baja la
 * versión paga completa, gratis y para siempre — sin loguearse siquiera.
 *
 * El workflow lo publica en el Release para que el dueño lo tenga a un clic,
 * pero CONDICIONADO a que el repositorio sea privado. Este archivo fija esa
 * condición: es una línea que se borra sin querer en cualquier refactor del
 * YAML, y el día que se borre no falla nada visible — simplemente el
 * producto queda regalado y nadie se entera.
 *
 * También fija el orden de los dos builds de Electron, que es la otra forma
 * conocida de que el instalador de CLIENTES salga con la licencia del
 * propietario adentro.
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const YML = path.join(__dirname, "..", "..", ".github", "workflows", "build-desktop.yml");
const yml = fs.readFileSync(YML, "utf8");

const GITIGNORE = fs.readFileSync(
  path.join(__dirname, "..", "..", ".gitignore"), "utf8");

(async () => {
  console.log("\n== El instalador del propietario no puede filtrarse ==");

  await test("EL RELEASE DEL OWNER ESTÁ CONDICIONADO A REPO PRIVADO", () => {
    const i = yml.indexOf("gh release upload");
    assert.ok(i > 0, "no se encontró el paso que sube el instalador al Release");
    // El `if:` del paso tiene que estar ANTES del comando, dentro del mismo paso.
    const inicioPaso = yml.lastIndexOf("\n      - name:", i);
    const bloque = yml.slice(inicioPaso, i);
    assert.match(bloque, /if:\s*github\.event\.repository\.private/,
      "el paso que sube el instalador del propietario al Release NO está " +
      "condicionado a que el repositorio sea privado: en un repo público " +
      "ese asset lo baja cualquiera sin loguearse");
  });

  await test("solo se sube al Release el .exe del PROPIETARIO por esa vía", () => {
    // Si alguien apuntara ese `gh release upload` al .exe del cliente
    // (o a un glob), la condición de repo privado dejaría de proteger nada.
    const linea = yml.split("\n").find((l) => l.includes("gh release upload"));
    assert.match(linea, /MV-SQL-NLP-App-Setup-OWNER\.exe/,
      `el upload condicionado no apunta al .exe del propietario: ${linea.trim()}`);
  });

  await test("la build de CLIENTES corre ANTES de generar la licencia del propietario", () => {
    // Es la otra forma de regalar el producto: si la licencia existe cuando
    // se compila el instalador público, el extraResources la mete adentro y
    // TODO cliente recibe acceso hasta 2099.
    // Se buscan los PASOS, no las menciones: el comentario que documenta
    // este mismo orden nombra licencia_owner.json antes de que exista, así
    // que buscar el string suelto da un falso positivo.
    const buildCliente = yml.indexOf("--publish=always");
    const generaLicencia = yml.indexOf("- name: Generar la licencia del propietario");
    assert.ok(buildCliente > 0 && generaLicencia > 0, "faltan los pasos esperados");
    assert.ok(buildCliente < generaLicencia,
      "la licencia del propietario se genera ANTES de compilar el instalador " +
      "de clientes: ese instalador saldría con acceso hasta 2099");
  });

  await test("la build del propietario NO publica al Release por sí misma", () => {
    // electron-builder tiene que correr con --publish=never para el owner:
    // si publicara solo, se saltearía la guarda de repo privado de arriba.
    const i = yml.indexOf("Generar instalador del propietario");
    const bloque = yml.slice(i, i + 2000);
    assert.match(bloque, /--publish=never/,
      "la build del propietario no lleva --publish=never: publicaría sola, " +
      "salteándose la condición de repositorio privado");
  });

  await test("los artefactos con licencia real siguen fuera del repo", () => {
    for (const ruta of ["desktop/licencia_owner.json",
                        "paquete/mvsql-nlp-app-OWNER.zip",
                        "owner/dist/"]) {
      assert.ok(GITIGNORE.includes(ruta),
        `${ruta} salió de .gitignore: lleva la licencia hasta 2099 adentro`);
    }
  });

  await test("la plantilla del conversor que SÍ se versiona no trae licencia real", () => {
    // owner/plantilla-convertir-a-dueno.ps1 se commitea a propósito, pero
    // con un marcador en vez de la licencia: si alguien la baja del repo
    // público y la corre, el propio script se planta.
    const plantilla = fs.readFileSync(
      path.join(__dirname, "..", "..", "owner", "plantilla-convertir-a-dueno.ps1"), "utf8");
    assert.ok(plantilla.includes("@@LICENCIA_OWNER_JSON@@"),
      "la plantilla perdió el marcador: ¿le quedó una licencia real adentro?");
    assert.ok(!plantilla.includes("2099-12-31"),
      "¡LA PLANTILLA VERSIONADA TIENE UNA LICENCIA REAL ADENTRO!");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
