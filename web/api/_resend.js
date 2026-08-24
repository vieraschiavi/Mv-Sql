/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — envío de mail transaccional (Resend), sin SDK.
//
// Lo usan solicitar-demo.js (pedido de demo) y _aviso-compra.js (alguien
// generó un link de pago). No justifica sumar el paquete `resend` como
// dependencia — la API es un POST con JSON, igual de simple hecha con
// fetch. Mismo criterio que verify-and-issue.js con la consulta de
// preapproval a MercadoPago.
//
// "from" usa el dominio sandbox de Resend (onboarding@resend.dev) por
// default: funciona sin verificar ningún dominio propio. El día que
// mvsqlnlp.com esté registrado y verificado en Resend, alcanza con
// poner RESEND_FROM en Vercel — no hace falta tocar código.
const DESDE_DEFECTO = "MV SQL NLP <onboarding@resend.dev>";

async function enviarMail({ para, asunto, texto, replyTo }) {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    throw new Error("Falta configurar RESEND_API_KEY en las variables de entorno de Vercel.");
  }
  const cuerpo = {
    from: process.env.RESEND_FROM || DESDE_DEFECTO,
    to: [para],
    subject: asunto,
    text: texto,
  };
  if (replyTo) cuerpo.reply_to = replyTo;

  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(cuerpo),
  });
  if (!r.ok) {
    const detalle = await r.text().catch(() => "");
    throw new Error(`Resend respondió ${r.status}: ${detalle.slice(0, 300)}`);
  }
  return r.json();
}

module.exports = { enviarMail };
