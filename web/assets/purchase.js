/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — flujo de compra (Checkout Pro de MercadoPago)

// Tasa de referencia USD → UYU (peso uruguayo). Es un valor aproximado para
// mostrar al lado del precio en dólares — no es cotización en vivo. Antes de
// vender en volumen, conviene reemplazar esto por una API de cambio real
// (ej. https://open.er-api.com) o actualizar el número manualmente cada tanto.
const USD_TO_UYU = 40;

function pintarPreciosUyu() {
  document.querySelectorAll(".price[data-usd]").forEach((el) => {
    const usd = Number(el.dataset.usd);
    const uyu = Math.round(usd * USD_TO_UYU / 10) * 10; // redondeado a $10
    const span = el.querySelector(".price-uyu");
    if (span) span.textContent = `≈ UYU ${uyu.toLocaleString("es-UY")}`;
  });
}


async function mvsqlComprar(plan, mode) {
  const status = document.getElementById("buy-status");
  const emailInput = document.getElementById("buy-email");
  const email = (emailInput?.value || "").trim();
  const dict = (window.I18N && window.I18N[window.LANG]) || {};

  // Mismo criterio que el servidor (web/api/_guard.js): si acá pasara algo
  // que allá se rechaza, el comprador viajaría a MercadoPago para volver
  // con un error. Sin < > " ' / \ ni espacios.
  if (!email || !/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email)) {
    status.textContent = dict.email_error || "Ingresá un email válido para recibir tu licencia.";
    status.style.color = "#f87171";
    emailInput?.focus();
    return;
  }

  status.style.color = "var(--muted)";
  status.textContent = dict.redirecting || "Te llevamos a MercadoPago…";

  // Sin esto, dos clics seguidos creaban DOS preferencias de pago en
  // MercadoPago. Se bloquean todos los botones de compra mientras dura
  // el pedido y se sueltan si algo sale mal.
  const botones = document.querySelectorAll('button[onclick*="mvsqlComprar"]');
  botones.forEach((b) => { b.disabled = true; });
  const soltar = () => botones.forEach((b) => { b.disabled = false; });

  const fallar = (texto) => {
    status.style.color = "#f87171";
    status.textContent = texto;
    soltar();
  };

  // Si la función serverless queda colgada (arranque en frío + MercadoPago
  // lento), sin corte el usuario se quedaba mirando "Te llevamos a
  // MercadoPago…" para siempre, con el botón activo y sin salida.
  const corte = new AbortController();
  const reloj = setTimeout(() => corte.abort(), 20000);

  try {
    // Las suscripciones van por preapproval (cobro mensual); el resto por
    // preferencia (pago único).
    const esSuscripcion = mode === "suscripcion";
    const r = await fetch(
      esSuscripcion ? "/api/create-subscription" : "/api/create-preference", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(esSuscripcion ? { plan, email } : { plan, mode, email }),
      signal: corte.signal,
    });
    let data = null;
    try { data = await r.json(); } catch { /* respuesta no-JSON */ }

    if (r.status === 429) {
      return fallar(dict.pago_muchos ||
        "Demasiados intentos seguidos. Esperá un minuto y probá otra vez.");
    }
    if (!r.ok || !data || !data.init_point) {
      return fallar((data && data.error) || dict.pago_error ||
        "No se pudo iniciar el pago. Probá de nuevo en un momento.");
    }
    location.href = data.init_point;
  } catch (e) {
    // El detalle técnico ("Failed to fetch") va a la consola: al comprador
    // no le dice nada y lo asusta.
    console.error("crear pago:", e);
    fallar(e.name === "AbortError"
      ? (dict.pago_timeout ||
         "MercadoPago está tardando más de lo normal. Probá de nuevo.")
      : (dict.pago_sin_red ||
         "No pudimos conectarnos. Revisá tu conexión y probá de nuevo."));
  } finally {
    clearTimeout(reloj);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  pintarPreciosUyu();
});

window.mvsqlComprar = mvsqlComprar;
