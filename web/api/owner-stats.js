// MV SQL NLP — GET /api/owner-stats?token=...  (panel del dueño)
// Consulta las ventas reales en MercadoPago y devuelve KPIs del negocio.
// No usa base de datos: MercadoPago ES la fuente de verdad de las ventas.
//
// Protegido por OWNER_TOKEN (variable de entorno en Vercel). Sin ese token
// configurado el endpoint queda cerrado — nunca abierto por defecto.
const { PRODUCTS } = require("./_products.js");
const { limitar } = require("./_guard.js");

const MESES = ["ene", "feb", "mar", "abr", "may", "jun",
               "jul", "ago", "set", "oct", "nov", "dic"];

function comparacionSegura(a, b) {
  // Comparación de token en tiempo constante: evita adivinar el token
  // midiendo cuánto tarda en responder.
  const A = Buffer.from(String(a));
  const B = Buffer.from(String(b));
  if (A.length !== B.length) return false;
  let dif = 0;
  for (let i = 0; i < A.length; i++) dif |= A[i] ^ B[i];
  return dif === 0;
}

module.exports = async (req, res) => {
  if (!limitar(req, res, { max: 30, ventanaMs: 60_000, nombre: "owner" })) return;
  const esperado = process.env.OWNER_TOKEN;
  if (!esperado) {
    return res.status(503).json({ error: "Panel no configurado: falta OWNER_TOKEN en Vercel." });
  }
  const token = req.query.token || "";
  if (!comparacionSegura(token, esperado)) {
    return res.status(401).json({ error: "Token inválido." });
  }

  const mpToken = process.env.MP_ACCESS_TOKEN;
  if (!mpToken) return res.status(500).json({ error: "Falta MP_ACCESS_TOKEN." });

  try {
    const desde = new Date();
    desde.setMonth(desde.getMonth() - 12);

    const r = await fetch(
      "https://api.mercadopago.com/v1/payments/search?sort=date_created&criteria=desc&limit=200" +
      `&begin_date=${desde.toISOString()}&end_date=NOW`,
      { headers: { Authorization: `Bearer ${mpToken}` } }
    );
    if (!r.ok) {
      return res.status(r.status).json({ error: `MercadoPago respondió ${r.status}.` });
    }
    const data = await r.json();
    const pagos = data.results || [];

    const aprobados = pagos.filter((p) => p.status === "approved");
    const ahora = new Date();
    const claveMes = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const mesActual = claveMes(ahora);

    const porMes = {};
    const porProducto = {};
    const clientes = new Set();
    let totalUSD = 0;

    for (const p of aprobados) {
      const fecha = new Date(p.date_approved || p.date_created);
      const mes = claveMes(fecha);
      const monto = Number(p.transaction_amount) || 0;
      totalUSD += monto;
      porMes[mes] = (porMes[mes] || 0) + monto;

      const ref = String(p.external_reference || "");
      const [plan, modo, email] = ref.split(":");
      const clave = plan && modo ? `${plan}:${modo}` : "desconocido";
      if (!porProducto[clave]) porProducto[clave] = { unidades: 0, usd: 0 };
      porProducto[clave].unidades += 1;
      porProducto[clave].usd += monto;
      if (email) clientes.add(email.toLowerCase());
    }

    const serie = Object.keys(porMes).sort().map((m) => {
      const [a, mm] = m.split("-");
      return { mes: `${MESES[Number(mm) - 1]} ${a.slice(2)}`, usd: porMes[m] };
    });

    const rechazados = pagos.filter((p) => p.status === "rejected").length;
    const pendientes = pagos.filter((p) => p.status === "pending" ||
                                           p.status === "in_process").length;

    res.status(200).json({
      generado: ahora.toISOString(),
      resumen: {
        ventas_totales: aprobados.length,
        ingreso_total_usd: Math.round(totalUSD),
        ingreso_mes_actual_usd: Math.round(porMes[mesActual] || 0),
        ticket_promedio_usd: aprobados.length
          ? Math.round(totalUSD / aprobados.length) : 0,
        clientes_unicos: clientes.size,
        pagos_rechazados: rechazados,
        pagos_pendientes: pendientes,
        tasa_aprobacion: pagos.length
          ? Math.round((aprobados.length / pagos.length) * 100) : 0,
      },
      por_mes: serie,
      por_producto: Object.entries(porProducto)
        .map(([k, v]) => ({
          producto: PRODUCTS[k] ? PRODUCTS[k].title : k,
          clave: k, unidades: v.unidades, usd: Math.round(v.usd),
        }))
        .sort((a, b) => b.usd - a.usd),
      ultimas_ventas: aprobados.slice(0, 15).map((p) => ({
        fecha: (p.date_approved || p.date_created || "").slice(0, 10),
        monto_usd: Number(p.transaction_amount) || 0,
        referencia: p.external_reference || "",
        medio: p.payment_method_id || "",
      })),
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
