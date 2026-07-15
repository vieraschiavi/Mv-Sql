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

let BUY_MODE = "own_ai";

// Descripciones del modo de compra (es = default; en/pt vienen del I18N de la página)
const BUY_DESC_ES = {
  byok_desc: "Traés tu propia clave de IA (Claude, ChatGPT, Gemini, Copilot…) y pagás " +
             "solo la licencia del programa. Ideal si ya usás IA.",
  credits_desc: "La IA ya viene incluida y medida por créditos — cero configuración. " +
                "Nosotros facturamos la IA por vos.",
};

function setBuyMode(mode) {
  BUY_MODE = mode;
  document.getElementById("plans-own_ai").style.display = mode === "own_ai" ? "grid" : "none";
  document.getElementById("plans-credits").style.display = mode === "credits" ? "grid" : "none";
  document.querySelectorAll("[data-buymode]").forEach((b) =>
    b.classList.toggle("active", b.dataset.buymode === mode));
  const desc = document.getElementById("buy-mode-desc");
  if (desc) {
    const key = mode === "own_ai" ? "byok_desc" : "credits_desc";
    const dict = (window.I18N && window.I18N[window.LANG]) || null;
    desc.innerHTML = (dict && dict[key]) || BUY_DESC_ES[key];
  }
}

async function mvsqlComprar(plan, mode) {
  const status = document.getElementById("buy-status");
  const emailInput = document.getElementById("buy-email");
  const email = (emailInput?.value || "").trim();
  const dict = (window.I18N && window.I18N[window.LANG]) || {};

  if (!email || !/^\S+@\S+\.\S+$/.test(email)) {
    status.textContent = dict.email_error || "Ingresá un email válido para recibir tu licencia.";
    status.style.color = "#f87171";
    emailInput?.focus();
    return;
  }

  status.style.color = "var(--muted)";
  status.textContent = dict.redirecting || "Te llevamos a MercadoPago…";

  try {
    const r = await fetch("/api/create-preference", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ plan, mode, email }),
    });
    const data = await r.json();
    if (!r.ok || !data.init_point) {
      status.style.color = "#f87171";
      status.textContent = data.error || "No se pudo iniciar el pago. Probá de nuevo.";
      return;
    }
    location.href = data.init_point;
  } catch (e) {
    status.style.color = "#f87171";
    status.textContent = "Error de conexión: " + e.message;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-buymode]").forEach((b) =>
    b.addEventListener("click", () => setBuyMode(b.dataset.buymode)));
  pintarPreciosUyu();
});

window.mvsqlComprar = mvsqlComprar;
