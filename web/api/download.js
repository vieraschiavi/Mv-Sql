// MV SQL NLP — GET /api/download?token=...
// Sirve el paquete descargable, gateado por la licencia emitida tras el pago.
//   mode "own_ai":  zip base tal cual — el cliente configura su propia API key.
//   mode "credits": zip base + licencia_mvsql.json embebida con los créditos
//                   comprados, lista para usar sin configurar nada
//                   (mismo espíritu que el zip de ejemplo original).
const fs = require("fs");
const path = require("path");
const JSZip = require("jszip");
const { verifyLicense } = require("./_license.js");

module.exports = async (req, res) => {
  try {
    const { token } = req.query;
    if (!token) return res.status(400).send("Falta el token de descarga. Comprá desde mvsqlnlp.com.");

    const license = verifyLicense(token);
    const zipPath = path.join(process.cwd(), "downloads", "mvsql-nlp-app.zip");
    const baseZip = fs.readFileSync(zipPath);

    res.setHeader("Content-Disposition", 'attachment; filename="MV-SQL-NLP.zip"');
    res.setHeader("Content-Type", "application/zip");

    if (license.mode !== "credits") {
      return res.status(200).send(baseZip);
    }

    const zip = await JSZip.loadAsync(baseZip);
    zip.file(
      "nl2sql_rag/licencia_mvsql.json",
      JSON.stringify({
        producto: "MV SQL NLP",
        email: license.email,
        plan: license.plan,
        creditos: license.credits,
        token,
        emitida: new Date(license.iat * 1000).toISOString(),
        vence: new Date(license.exp * 1000).toISOString(),
        proxy_url: `https://${req.headers.host}/api/ai-proxy`,
        nota: "No compartas este archivo: contiene tu token de créditos. Elegí el proveedor 'MV SQL Créditos' en la app — no hace falta ninguna API key.",
      }, null, 2)
    );
    const out = await zip.generateAsync({ type: "nodebuffer" });
    res.status(200).send(out);
  } catch (e) {
    res.status(401).send(`No se pudo validar la descarga: ${e.message}`);
  }
};
