/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — avisa por mail al dueño el momento en que alguien hace clic
// en "Comprar"/"Suscribirme" (create-preference / create-subscription), no
// cuando el pago se confirma. Sirve para no activar un plan pago (por
// ejemplo Vercel Pro en varios proyectos) a ciegas, "por si acaso": lo
// activás justo cuando aparece intención de compra real.
//
// Best-effort a propósito: si Resend falla o RESEND_API_KEY no está
// configurada, el checkout tiene que seguir funcionando igual — este aviso
// es un extra, nunca puede tumbar un cobro. Por eso enviarMail() se llama
// siempre adentro de un try/catch que se traga el error (solo lo loguea).
//
// Con guarda de idempotencia: un cliente indeciso que toca "Comprar" varias
// veces en la misma visita no tiene que generar un mail por click. La clave
// vive en memoria del proceso — mismo límite que _guard.js: por instancia
// de Vercel, se reinicia en frío. Alcanza para el caso real (varios clicks
// seguidos en la misma visita), no pretende ser una deduplicación exacta
// entre instancias.
const { enviarMail } = require("./_resend.js");

const VENTANA_MS = 30 * 60 * 1000; // 30 min: cubre un mismo intento de compra
const _avisados = new Map();

function _yaAvisado(clave) {
  const ahora = Date.now();
  if (_avisados.size > 2000) {
    for (const [k, hasta] of _avisados) if (ahora > hasta) _avisados.delete(k);
  }
  const hasta = _avisados.get(clave);
  if (hasta && ahora < hasta) return true;
  _avisados.set(clave, ahora + VENTANA_MS);
  return false;
}

/**
 * Avisa que alguien generó un link de pago (todavía no que pagó).
 * Nunca lanza: un fallo acá no puede romper el checkout.
 */
async function avisarIntentoDeCompra({ plan, modo, email, producto }) {
  const clave = `${plan}:${modo}:${email}`;
  if (_yaAvisado(clave)) return { enviado: false, motivo: "duplicado" };
  try {
    await enviarMail({
      para: "vieraschiavi@gmail.com",
      asunto: `Intención de compra: ${producto?.title || plan} (${email})`,
      texto: [
        `Alguien generó el link de pago de ${producto?.title || plan}.`,
        "",
        `Plan: ${plan}`,
        `Modalidad: ${modo}`,
        `Monto: US$${producto?.price ?? "?"}`,
        `Email: ${email}`,
        `Hora: ${new Date().toISOString()}`,
        "",
        "Esto es intención de compra (recién generó el link, no pagó todavía). " +
          "La confirmación real llega por el webhook de MercadoPago cuando el pago se aprueba.",
      ].join("\n"),
      replyTo: email,
    });
    return { enviado: true };
  } catch (e) {
    console.warn("[mvsql aviso-compra] no se pudo avisar:", e.message);
    return { enviado: false, motivo: e.message };
  }
}

module.exports = { avisarIntentoDeCompra, _yaAvisado };
