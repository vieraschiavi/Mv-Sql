/** El zip que descarga el que paga coincide con el fuente de app-python.
 *
 * /api/download sirve web/downloads/mvsql-nlp-app.zip tal cual está en el
 * repo. Ese zip se genera con tools/empaquetar_zip.py, pero nada obligaba a
 * regenerarlo: se commiteó una vez y quedó congelado mientras app-python/
 * seguía cambiando. Resultado real detectado por la auditoría: el cliente
 * compraba, pagaba, descargaba — y recibía una versión vieja del programa,
 * sin los arreglos de seguridad y privacidad de las últimas semanas.
 *
 * Este test falla si CUALQUIER archivo del zip difiere del fuente. La CI lo
 * corre en cada push, así que un cambio en app-python/ sin regenerar el zip
 * rompe el build en vez de llegar en silencio al cliente que pagó.
 *
 * Requiere Node (unzip vía zlib, sin dependencias). Los .pyd compilados por
 * Cython no están en el fuente y se saltean: el zip de release los trae, pero
 * este chequeo mira el árbol de desarrollo.
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const ZIP = path.join(RAIZ, "web", "downloads", "mvsql-nlp-app.zip");
const SRC = path.join(RAIZ, "app-python");

// Lector de ZIP mínimo: recorre el End Of Central Directory y las entradas.
// Solo necesita nombre + contenido de cada archivo, y soporta STORE (0) y
// DEFLATE (8), que es lo único que produce zipfile de Python.
function leerZip(buf) {
  const archivos = {};
  // Fin del directorio central: se busca la firma 0x06054b50 desde el final.
  let eocd = buf.length - 22;
  while (eocd >= 0 && buf.readUInt32LE(eocd) !== 0x06054b50) eocd--;
  assert.ok(eocd >= 0, "el zip no tiene End Of Central Directory (¿corrupto?)");
  let ptr = buf.readUInt32LE(eocd + 16);           // offset del directorio central
  const n = buf.readUInt16LE(eocd + 10);
  for (let i = 0; i < n; i++) {
    assert.strictEqual(buf.readUInt32LE(ptr), 0x02014b50, "entrada de directorio inválida");
    const metodo = buf.readUInt16LE(ptr + 10);
    const compSize = buf.readUInt32LE(ptr + 20);
    const nameLen = buf.readUInt16LE(ptr + 28);
    const extraLen = buf.readUInt16LE(ptr + 30);
    const commentLen = buf.readUInt16LE(ptr + 32);
    const lho = buf.readUInt32LE(ptr + 42);        // offset de la cabecera local
    const nombre = buf.toString("utf8", ptr + 46, ptr + 46 + nameLen);
    // La cabecera local repite name/extra con sus propios largos.
    const lNameLen = buf.readUInt16LE(lho + 26);
    const lExtraLen = buf.readUInt16LE(lho + 28);
    const dataIni = lho + 30 + lNameLen + lExtraLen;
    const comp = buf.subarray(dataIni, dataIni + compSize);
    if (!nombre.endsWith("/")) {
      archivos[nombre] = metodo === 8 ? zlib.inflateRawSync(comp) : Buffer.from(comp);
    }
    ptr += 46 + nameLen + extraLen + commentLen;
  }
  return archivos;
}

(async () => {
  console.log("\n== El zip descargable está al día con app-python/ ==");

  await test("el zip existe y se puede leer", () => {
    assert.ok(fs.existsSync(ZIP), "falta web/downloads/mvsql-nlp-app.zip");
    const a = leerZip(fs.readFileSync(ZIP));
    assert.ok(Object.keys(a).length > 5, "el zip tiene sospechosamente pocos archivos");
  });

  await test("ningún archivo del zip difiere del fuente de app-python", () => {
    const archivos = leerZip(fs.readFileSync(ZIP));
    const raiz = Object.keys(archivos)[0].split("/")[0] + "/";
    const distintos = [];
    for (const [nombre, contenido] of Object.entries(archivos)) {
      const rel = nombre.slice(raiz.length);
      const fuente = path.join(SRC, rel);
      if (fs.existsSync(fuente) && !contenido.equals(fs.readFileSync(fuente))) {
        distintos.push(rel);
      }
    }
    assert.deepStrictEqual(distintos, [],
      "el zip publicado quedó viejo — corré `python3 tools/empaquetar_zip.py` y " +
      "commiteá el resultado. Archivos desactualizados: " + distintos.join(", "));
  });

  await test("EL ZIP DEL CLIENTE NO LLEVA LICENCIA ADENTRO", () => {
    // Este es el zip que sirve la web, a un clic de cualquiera. La
    // variante del propietario es el MISMO zip con un licencia_mvsql.json
    // que vence en 2099: si ese archivo se colara acá, el trial de 7 días
    // no aplicaría para nadie y el producto quedaría gratis y sin
    // vencimiento. Es el mismo error que ya se cometió publicando el .exe
    // del propietario en un Release, y no da ningún síntoma: el zip se
    // descarga igual, la app abre igual, solo que nunca vence.
    const archivos = leerZip(fs.readFileSync(ZIP));
    const licencias = Object.keys(archivos).filter((n) => /licencia_mvsql/.test(n));
    assert.deepStrictEqual(licencias, [],
      `el zip público lleva licencia embebida: ${licencias.join(", ")}`);
  });

  await test("el zip trae los archivos clave (no quedó un zip vacío)", () => {
    const archivos = leerZip(fs.readFileSync(ZIP));
    const nombres = Object.keys(archivos).map((n) => n.split("/").pop());
    for (const req of ["app.py", "motor.py", "conectores.py", "INICIAR_MVSQL.bat",
                       "requirements.txt", "licencia.py"]) {
      assert.ok(nombres.includes(req), `el zip no trae ${req}`);
    }
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
