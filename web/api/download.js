/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — GET /api/download?token=...
// Sirve el paquete descargable, gateado por la licencia emitida tras el pago.
// Los dos modos llevan licencia_mvsql.json embebida — sin eso, la app
// (app-python/licencia.py) trataría a un cliente que pagó como si fuera
// el trial gratuito y lo bloquearía a los 7 días igual que a cualquiera.
//   mode "own_ai":  zip + licencia_mvsql.json (sin proxy_url/créditos) —
//                   el cliente configura su propia API key, pero queda
//                   eximido del límite de trial.
//   mode "credits": zip + licencia_mvsql.json con los créditos comprados,
//                   lista para usar sin configurar nada (mismo espíritu
//                   que el zip de ejemplo original).
const fs = require("fs");
const path = require("path");
const JSZip = require("jszip");
const { verifyLicense } = require("./_license.js");
const { archivoLicencia } = require("./_licencia-archivo.js");
const { limitar } = require("./_guard.js");

// El zip está en paquete/, HERMANA de web/ (no adentro) — a propósito: todo
// lo que cuelga de web/ es lo que Vercel sirve como estático sin gate
// ninguno (outputDirectory: web), así que un archivo ahí es tan "público"
// como el resto de la landing aunque ningún botón lo enlace. paquete/ solo
// llega a esta función vía includeFiles (ver vercel.json) — nunca se sirve
// solo. Según desde dónde publique Vercel, el cwd de la función es uno u
// otro: se prueban varios candidatos en vez de asumir.
function rutaDelZip() {
  const candidatas = [
    path.join(process.cwd(), "paquete", "mvsql-nlp-app.zip"),
    path.join(process.cwd(), "..", "paquete", "mvsql-nlp-app.zip"),
    path.join(__dirname, "..", "..", "paquete", "mvsql-nlp-app.zip"),
  ];
  const encontrada = candidatas.find((p) => fs.existsSync(p));
  if (!encontrada) {
    throw new Error("No se encontró el paquete de descarga en el servidor.");
  }
  return encontrada;
}

module.exports = async (req, res) => {
  if (!limitar(req, res, { max: 20, ventanaMs: 60_000, nombre: "download" })) return;

  const { token } = req.query;
  if (!token) return res.status(400).send("Falta el token de descarga. Comprá desde mvsqlnlp.com.");

  // La licencia se valida aparte: es la ÚNICA falla que justifica un 401
  // ("tu licencia no sirve"). Antes cualquier error posterior —zip faltante,
  // fallo al generar— salía como 401 y le decía al que pagó que comprara de
  // nuevo por un problema del servidor.
  let license;
  try {
    license = verifyLicense(token);
  } catch {
    return res.status(401).send("Tu enlace de descarga no es válido o venció. Escribinos a vieraschiavi@gmail.com con tu comprobante.");
  }

  try {
    // La forma del archivo vive en _licencia-archivo.js, compartida con
    // /api/renovar-licencia: los dos escriben el MISMO archivo, y si cada
    // uno lo armara por su cuenta el segundo podría emitir una licencia a
    // la que le falte un campo que este sí pone.
    const licenciaJson = archivoLicencia(token, license, req.headers.host);

    // Todo el trabajo que puede fallar ocurre ANTES de tocar los headers:
    // leer el zip base y generar el zip final. Antes se seteaba
    // Content-Type: application/zip primero, así que si loadAsync/generateAsync
    // fallaban, el cliente descargaba un "MV-SQL-NLP.zip" que en realidad era
    // el texto del error — un archivo corrupto que no abre.
    const baseZip = fs.readFileSync(rutaDelZip());
    const zip = await JSZip.loadAsync(baseZip);
    zip.file("nl2sql_rag/licencia_mvsql.json", JSON.stringify(licenciaJson, null, 2));
    const out = await zip.generateAsync({ type: "nodebuffer" });

    // Recién acá, con el zip ya en mano, se declaran los headers de descarga.
    res.setHeader("Content-Disposition", 'attachment; filename="MV-SQL-NLP.zip"');
    res.setHeader("Content-Type", "application/zip");
    res.status(200).send(out);
  } catch (e) {
    // Error del servidor, no de la licencia: 500 y en texto plano (los headers
    // de zip todavía no se pusieron, así que esto no sale como archivo).
    console.error("[download]", e.message);
    res.status(500).send("No pudimos preparar tu descarga en este momento. Probá de nuevo en unos minutos o escribinos a vieraschiavi@gmail.com.");
  }
};
