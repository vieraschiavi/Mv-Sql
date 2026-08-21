/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — GET /api/download-licencia?token=...
// Sirve SOLO el archivo licencia_mvsql.json, sin el .zip alrededor.
//
// Por qué existe esto además de /api/download: ese endpoint entrega el
// producto Python completo con la licencia embebida adentro del zip
// (nl2sql_rag/licencia_mvsql.json) — perfecto para ese producto, pero
// inútil para quien ya tiene el programa de escritorio (Electron)
// instalado, cuya pantalla "Ya tengo una licencia" pide elegir un
// archivo .json suelto (ver desktop/electron/main.cjs, filtro de
// extensión "json"). Antes de este endpoint, la única forma de llegar a
// ese archivo era bajar el zip entero, abrirlo a mano y encontrar el
// .json enterrado adentro de nl2sql_rag/ — nada en la interfaz lo decía.
//
// Reusa exactamente los mismos helpers que /api/download (verifyLicense,
// archivoLicencia): es el MISMO contenido, solo que sin el zip alrededor.
const { verifyLicense } = require("./_license.js");
const { archivoLicencia } = require("./_licencia-archivo.js");
const { limitar } = require("./_guard.js");

module.exports = async (req, res) => {
  if (!limitar(req, res, { max: 20, ventanaMs: 60_000, nombre: "download-licencia" })) return;

  const { token } = req.query;
  if (!token) return res.status(400).send("Falta el token de descarga. Comprá desde mvsqlnlp.com.");

  let license;
  try {
    license = verifyLicense(token);
  } catch {
    return res.status(401).send("Tu enlace de descarga no es válido o venció. Escribinos a vieraschiavi@gmail.com con tu comprobante.");
  }

  try {
    const licenciaJson = archivoLicencia(token, license, req.headers.host);
    res.setHeader("Content-Disposition", 'attachment; filename="licencia_mvsql.json"');
    res.setHeader("Content-Type", "application/json");
    res.status(200).send(JSON.stringify(licenciaJson, null, 2));
  } catch (e) {
    console.error("[download-licencia]", e.message);
    res.status(500).send("No pudimos preparar tu licencia en este momento. Probá de nuevo en unos minutos o escribinos a vieraschiavi@gmail.com.");
  }
};
