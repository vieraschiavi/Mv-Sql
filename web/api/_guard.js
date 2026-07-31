// _guard.js — validación de entrada y rate limiting compartidos.
// ===================================================================
// Antes cada endpoint validaba (o no) por su cuenta, y ninguno tenía
// límite de pedidos. Dos consecuencias concretas que esto cierra:
//
//   1. El regex de email que se usaba (/^\S+@\S+\.\S+$/) aceptaba
//      "<svg/onload=alert(1)>@a.co": no tiene espacios, así que pasaba.
//      Ese valor termina dentro de external_reference y se muestra
//      después en el panel del dueño.
//   2. Sin rate limiting, /api/verify-and-issue se puede barrer por
//      fuerza bruta: recibe un payment_id, y si está aprobado emite la
//      licencia — sin pedir ninguna prueba de que quien llama es el
//      comprador.
//
// El contador vive en memoria del proceso. En Vercel cada instancia
// tiene la suya y se reinicia en frío, así que NO es un límite global
// exacto: es un freno de fuerza bruta, no una cuota. Se documenta así
// a propósito para no prometer lo que no da.
// ===================================================================

// Formato de email deliberadamente conservador: sin < > " ' ` / \ ni
// espacios, que son justo los caracteres con los que se arma un payload
// HTML. Rechaza direcciones exóticas pero válidas (comillas en la parte
// local); es un precio aceptable para un formulario de compra.
const EMAIL_OK = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

function emailValido(email) {
  return typeof email === "string" && email.length <= 254 && EMAIL_OK.test(email);
}

const _cubetas = new Map();

function limpiarVencidas(ahora) {
  for (const [k, v] of _cubetas) {
    if (ahora > v.hasta) _cubetas.delete(k);
  }
}

/**
 * Ventana fija por clave. Devuelve true si el pedido se permite.
 * @param {string} clave    normalmente la IP del que llama
 * @param {number} max      pedidos permitidos por ventana
 * @param {number} ventanaMs largo de la ventana
 */
function permitido(clave, max, ventanaMs) {
  const ahora = Date.now();
  if (_cubetas.size > 5000) limpiarVencidas(ahora); // techo de memoria
  const actual = _cubetas.get(clave);
  if (!actual || ahora > actual.hasta) {
    _cubetas.set(clave, { cuenta: 1, hasta: ahora + ventanaMs });
    return true;
  }
  actual.cuenta += 1;
  return actual.cuenta <= max;
}

function ipDe(req) {
  // Todo opcional a propósito: un req sin headers (o sin socket) no tiene
  // que tirar abajo el endpoint. Si no se puede identificar el origen, se
  // agrupa bajo "desconocida" — comparten cubeta, que es el lado seguro.
  const fwd = req?.headers?.["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim();
  return req?.socket?.remoteAddress || "desconocida";
}

/**
 * Aplica rate limiting y contesta 429 si se pasó.
 * Devuelve true si el handler puede seguir.
 */
function limitar(req, res, { max = 20, ventanaMs = 60_000, nombre = "" } = {}) {
  const clave = `${nombre}:${ipDe(req)}`;
  if (permitido(clave, max, ventanaMs)) return true;
  res.setHeader("Retry-After", Math.ceil(ventanaMs / 1000));
  res.status(429).send("Demasiados pedidos. Esperá un momento y probá de nuevo.");
  return false;
}

module.exports = { emailValido, limitar, permitido, ipDe, EMAIL_OK };
