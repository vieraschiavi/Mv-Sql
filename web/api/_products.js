/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — catálogo comercial.
//
// Modelo (corregido tras la auditoría de jul-2026): el producto es el
// diferenciador, el servicio de implementación es el negocio.
//   - "suscripcion": licencia mensual recurrente (MercadoPago preapproval).
//     El cliente pone su propia API key de IA, así que nuestro costo de IA es 0.
//   - "servicio": pago único de implementación sobre la BD/ERP del cliente,
//     y retainer mensual de soporte.
//   - "credits": paquete de créditos con nuestra IA embebida (pago único).
//
// Los precios SIEMPRE salen de acá, nunca del cliente: create-preference y
// create-subscription los leen de este catálogo (hay tests que lo verifican).

// Recurrentes — se cobran todos los meses hasta que el cliente cancele.
const SUSCRIPCIONES = {
  "personal:suscripcion": {
    title: "MV SQL NLP — Personal", price: 15, frequency: 1, frequency_type: "months",
    descripcion: "1 usuario · todas las bases · con tu propia API key",
  },
  "profesional:suscripcion": {
    title: "MV SQL NLP — Profesional", price: 29, frequency: 1, frequency_type: "months",
    descripcion: "1 usuario · stored procedures · optimizador CTE · conector MCP",
  },
  "empresa:suscripcion": {
    title: "MV SQL NLP — Empresa", price: 79, frequency: 1, frequency_type: "months",
    descripcion: "hasta 5 puestos · soporte prioritario · factura a la empresa",
  },
  "soporte:suscripcion": {
    title: "MV SQL NLP — Soporte y mantenimiento", price: 150, frequency: 1, frequency_type: "months",
    descripcion: "post-implementación: cambios de esquema, consultas nuevas, prioridad",
  },
};

// Pago único.
const UNICOS = {
  // El producto principal del negocio: conectar MV SQL NLP a la base/ERP real
  // del cliente, mapear su esquema y dejar las consultas de negocio andando.
  "implementacion:servicio": {
    title: "MV SQL NLP — Implementación sobre tu base de datos / ERP", price: 2500,
    descripcion: "relevamiento, conexión, mapeo del esquema, consultas de negocio y capacitación",
  },
  "implementacion_express:servicio": {
    title: "MV SQL NLP — Implementación Express (1 base, sin ERP)", price: 900,
    descripcion: "una sola base, esquema acotado, hasta 10 consultas de negocio",
  },
  // Los paquetes de créditos SE DEJARON DE VENDER. El modelo es que cada
  // cliente ponga su propia API key del proveedor que prefiera (Claude,
  // GPT, Gemini, Copilot...), así el costo de IA es suyo y nuestro es 0.
  //
  // Sacarlos de acá alcanza para dejar de venderlos: create-preference
  // lee los precios de este catálogo y rechaza cualquier clave que no
  // esté. Lo que NO se toca es el modo "credits" en _license.js,
  // download.js y ai-proxy.js — quien ya compró un paquete sigue
  // teniéndolo hasta que se le agote, y borrar esa rama le rompería el
  // producto que pagó.
};

const PRODUCTS = { ...UNICOS, ...SUSCRIPCIONES };

/** true si la clave plan:modo se cobra de forma recurrente. */
function esRecurrente(clave) {
  return Object.prototype.hasOwnProperty.call(SUSCRIPCIONES, clave);
}

module.exports = { PRODUCTS, SUSCRIPCIONES, UNICOS, esRecurrente };
