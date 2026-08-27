/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — GET /api/estado?token=OWNER_TOKEN
//
// Responde una sola pregunta: ¿está el sistema en condiciones de cobrarle
// a un cliente y entregarle lo que pagó?
//
// Existe porque desde afuera NO se puede saber. Si falta LICENSE_SECRET,
// /api/download devuelve 401 "tu enlace no es válido" — exactamente lo
// mismo que devuelve ante un token falsificado. Eso está bien como
// seguridad (no le cuenta a un atacante qué falta configurar) pero deja
// al dueño ciego: el modo de falla es un cliente que paga, vuelve a
// /gracias y no recibe la licencia, sin ninguna señal previa.
//
// Nunca devuelve el VALOR de ninguna variable, solo si está puesta o no.
// Y va detrás de OWNER_TOKEN, igual que el panel de ventas: qué le falta
// configurar a un negocio es información del negocio.
const { limitar } = require("./_guard.js");

// Cada variable, qué se rompe sin ella y dónde se carga.
const VARIABLES = [
  {
    nombre: "MP_ACCESS_TOKEN",
    critica: true,
    para: "Cobrar. Sin esto nadie puede ni generar el link de pago.",
    donde: "MercadoPago → Tus integraciones → Credenciales de producción",
  },
  {
    nombre: "LICENSE_SECRET",
    critica: true,
    para: "Firmar y validar las licencias. Sin esto el que paga no puede descargar nada.",
    donde: "Vercel → Settings → Environment Variables (no rotar una vez emitida la primera licencia)",
  },
  {
    nombre: "OWNER_TOKEN",
    critica: false,
    para: "Tu panel de ventas y este chequeo.",
    donde: "Vercel → Settings → Environment Variables",
  },
  {
    nombre: "RESEND_API_KEY",
    critica: false,
    para: "Avisarte por mail de los pedidos de demo y de la intención de compra. El cobro anda igual sin esto.",
    donde: "resend.com → API Keys",
  },
  {
    nombre: "ANTHROPIC_API_KEY",
    critica: false,
    para: "Solo el modo 'créditos embebidos', que hoy no se vende (cada cliente pone su propia API key).",
    donde: "console.anthropic.com → API Keys",
  },
  {
    nombre: "KV_REST_API_URL",
    critica: false,
    para: "Contador de créditos del modo embebido. Sin esto /api/ai-proxy falla cerrado, que es lo correcto.",
    donde: "Vercel → Storage → KV",
  },
];

function comparacionSegura(a, b) {
  const A = Buffer.from(String(a));
  const B = Buffer.from(String(b));
  if (A.length !== B.length) return false;
  let dif = 0;
  for (let i = 0; i < A.length; i++) dif |= A[i] ^ B[i];
  return dif === 0;
}

module.exports = async (req, res) => {
  if (!limitar(req, res, { max: 30, ventanaMs: 60_000, nombre: "estado" })) return;

  const esperado = process.env.OWNER_TOKEN;
  if (!esperado) {
    // Sin OWNER_TOKEN no hay con qué autenticar, así que no se puede
    // devolver el detalle. Se dice lo mínimo para poder destrabarlo:
    // que falta justamente esa variable.
    return res.status(503).json({
      listo_para_vender: false,
      error: "Falta OWNER_TOKEN en Vercel: es la variable que protege este chequeo.",
    });
  }
  if (!comparacionSegura(req.query.token || "", esperado)) {
    return res.status(401).json({ error: "Token inválido." });
  }

  const variables = VARIABLES.map((v) => ({
    ...v,
    configurada: Boolean(process.env[v.nombre]),
  }));
  const faltantes = variables.filter((v) => !v.configurada);
  const criticasFaltantes = faltantes.filter((v) => v.critica);

  res.status(200).json({
    generado: new Date().toISOString(),
    // La pregunta que importa: ¿un cliente que paga hoy recibe lo que compró?
    listo_para_vender: criticasFaltantes.length === 0,
    resumen: criticasFaltantes.length === 0
      ? (faltantes.length === 0
        ? "Todo configurado."
        : `Se puede cobrar y entregar. Faltan ${faltantes.length} variable(s) no crítica(s).`)
      : `NO se puede vender: falta ${criticasFaltantes.map((v) => v.nombre).join(", ")}.`,
    variables,
    faltan_criticas: criticasFaltantes.map((v) => v.nombre),
  });
};
