/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — GET /api/download-instalador?token=...
// Sirve MV-SQL-NLP-Setup.exe (el instalador Windows completo del producto
// Python) detrás del mismo gate de licencia que /api/download.
//
// Antes de este endpoint, ese .exe era un link público sin ningún chequeo
// — cualquiera lo bajaba, pagara o no. Al sacar la descarga pública del
// trial (ver web/api/solicitar-demo.js), ese archivo se queda sin ninguna
// vía de entrega para el cliente que SÍ pagó, salvo que exista esto: no
// tenía (a diferencia de mvsql-nlp-app.zip) ningún endpoint que lo
// entregara gateado.
//
// El .exe no lleva la licencia embebida como el zip (NSIS no la mete
// adentro del instalador en tiempo de descarga): el cliente instala con
// esto y activa con el archivo de /api/download-licencia, exactamente
// igual que el programa de escritorio Electron. Un solo mecanismo de
// licencia para los dos formatos de instalador de Windows.
const fs = require("fs");
const path = require("path");
const { verifyLicense } = require("./_license.js");
const { limitar } = require("./_guard.js");

function rutaDelInstalador() {
  const candidatas = [
    path.join(process.cwd(), "paquete", "MV-SQL-NLP-Setup.exe"),
    path.join(process.cwd(), "..", "paquete", "MV-SQL-NLP-Setup.exe"),
    path.join(__dirname, "..", "..", "paquete", "MV-SQL-NLP-Setup.exe"),
  ];
  const encontrada = candidatas.find((p) => fs.existsSync(p));
  if (!encontrada) {
    throw new Error("No se encontró el instalador en el servidor.");
  }
  return encontrada;
}

module.exports = async (req, res) => {
  if (!limitar(req, res, { max: 20, ventanaMs: 60_000, nombre: "download-instalador" })) return;

  const { token } = req.query;
  if (!token) return res.status(400).send("Falta el token de descarga. Comprá desde mvsqlnlp.com.");

  try {
    verifyLicense(token);
  } catch {
    return res.status(401).send("Tu enlace de descarga no es válido o venció. Escribinos a vieraschiavi@gmail.com con tu comprobante.");
  }

  try {
    const archivo = fs.readFileSync(rutaDelInstalador());
    res.setHeader("Content-Disposition", 'attachment; filename="MV-SQL-NLP-Setup.exe"');
    res.setHeader("Content-Type", "application/octet-stream");
    res.status(200).send(archivo);
  } catch (e) {
    console.error("[download-instalador]", e.message);
    res.status(500).send("No pudimos preparar tu descarga en este momento. Probá de nuevo en unos minutos o escribinos a vieraschiavi@gmail.com.");
  }
};
