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

function setBuyMode(mode) {
  BUY_MODE = mode;
  document.getElementById("plans-own_ai").style.display = mode === "own_ai" ? "grid" : "none";
  document.getElementById("plans-credits").style.display = mode === "credits" ? "grid" : "none";
  document.querySelectorAll("[data-buymode]").forEach((b) =>
    b.classList.toggle("active", b.dataset.buymode === mode));
  const desc = document.getElementById("buy-mode-desc");
  if (desc) desc.setAttribute("data-i18n", mode === "own_ai" ? "byok_desc" : "credits_desc");
  if (window.applyLang) applyLang(window.LANG || "es");
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
