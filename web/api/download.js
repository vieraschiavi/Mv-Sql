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

// El zip está en web/downloads/. Según desde dónde publique Vercel (la raíz
// del repo o web/), el cwd de la función es uno u otro: se prueban ambos en
// vez de asumir, que es lo que hacía que la descarga fallara al mover la raíz.
function rutaDelZip() {
  const candidatas = [
    path.join(process.cwd(), "downloads", "mvsql-nlp-app.zip"),
    path.join(process.cwd(), "web", "downloads", "mvsql-nlp-app.zip"),
    path.join(__dirname, "..", "downloads", "mvsql-nlp-app.zip"),
  ];
  const encontrada = candidatas.find((p) => fs.existsSync(p));
  if (!encontrada) {
    throw new Error("No se encontró el paquete de descarga en el servidor.");
  }
  return encontrada;
}

module.exports = async (req, res) => {
  try {
    const { token } = req.query;
    if (!token) return res.status(400).send("Falta el token de descarga. Comprá desde mvsqlnlp.com.");

    const license = verifyLicense(token);
    const baseZip = fs.readFileSync(rutaDelZip());

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
