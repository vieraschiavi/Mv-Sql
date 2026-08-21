/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — POST /api/solicitar-demo { nombre, pais, empresa, email }
//
// Reemplaza la descarga pública del trial. Antes, cualquiera —cliente
// real o competencia mirando cómo está armado el producto— bajaba el
// instalador sin dejar rastro. Ahora la demo se pide, y cada pedido
// llega por mail con quién la pidió: filtra curiosidad de prospecto
// serio, y no regala el artefacto de ingeniería a quien solo quiere
// mirarlo por dentro.
const { enviarMail } = require("./_resend.js");
const { emailValido, limitar } = require("./_guard.js");

const CAMPO_MAX = 200;

// Mismo criterio que el email: sin < > " ' ` / \ ni saltos de línea. Estos
// campos van al CUERPO del mail (texto plano, nunca a un header), así que
// no hay riesgo de inyección de headers — pero sí de que alguien mande un
// "nombre" con HTML pensando en que algún día esto se muestre en el panel
// del dueño. Se corta corto para no heredar ese problema si eso pasa.
function textoValido(v) {
  return typeof v === "string" && v.trim().length > 0 && v.length <= CAMPO_MAX &&
    !/[<>"'`\\\r\n]/.test(v);
}

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido." });
  // Más estricto que /api/create-preference: esto no cobra nada, así que
  // el único costo de un abuso es llenarme la bandeja de entrada.
  if (!limitar(req, res, { max: 5, ventanaMs: 60_000, nombre: "demo" })) return;

  const { nombre, pais, empresa, email } = req.body || {};
  if (!textoValido(nombre) || !textoValido(pais) || !textoValido(empresa)) {
    return res.status(400).json({ error: "Completá nombre, país y empresa." });
  }
  if (!emailValido(email)) {
    return res.status(400).json({ error: "Ingresá un email válido." });
  }

  try {
    await enviarMail({
      para: "vieraschiavi@gmail.com",
      asunto: `Demo MV SQL NLP — ${empresa}`,
      texto: `Nueva solicitud de demo desde mvsqlnlp.com\n\n` +
        `Nombre completo: ${nombre}\n` +
        `País: ${pais}\n` +
        `Empresa: ${empresa}\n` +
        `Email: ${email}\n`,
      replyTo: email,
    });
    res.status(200).json({ ok: true });
  } catch (e) {
    console.error("[solicitar-demo]", e.message);
    res.status(500).json({
      error: "No pudimos enviar tu pedido en este momento. Escribinos directo a vieraschiavi@gmail.com.",
    });
  }
};
