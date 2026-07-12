/* MV SQL NLP — landing interactions: i18n, pricing toggle, terminal demo */

// ── i18n ─────────────────────────────────────────────
const LANGS = ["es", "en", "pt"];

function detectLang() {
  const q = new URLSearchParams(location.search).get("lang");
  if (LANGS.includes(q)) return q;
  const saved = localStorage.getItem("mvsql_lang");
  if (LANGS.includes(saved)) return saved;
  const nav = (navigator.language || "es").slice(0, 2);
  return LANGS.includes(nav) ? nav : "es";
}

var LANG = detectLang();

function applyLang(lang) {
  LANG = lang;
  localStorage.setItem("mvsql_lang", lang);
  document.documentElement.lang = lang;
  const dict = I18N[lang];
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key] !== undefined) el.innerHTML = dict[key];
  });
  document.querySelectorAll(".lang-switch button").forEach((b) =>
    b.classList.toggle("active", b.dataset.lang === lang));
  restartDemo();
}

// ── pricing toggle (suscripción / créditos) ─────────
function setPricingMode(mode) {
  document.getElementById("plans-sub").style.display = mode === "sub" ? "grid" : "none";
  document.getElementById("plans-cred").style.display = mode === "cred" ? "grid" : "none";
  document.querySelectorAll(".pricing-toggle button").forEach((b) =>
    b.classList.toggle("active", b.dataset.mode === mode));
}

// ── demo animada del terminal (sin lag: rAF + timeouts cortos) ──
const demoTimeouts = [];
function later(fn, ms) { demoTimeouts.push(setTimeout(fn, ms)); }

function typeText(el, text, speed, done) {
  let i = 0;
  (function tick() {
    if (i <= text.length) {
      el.textContent = text.slice(0, i);
      i++;
      demoTimeouts.push(setTimeout(tick, speed));
    } else if (done) done();
  })();
}

function restartDemo() {
  demoTimeouts.forEach(clearTimeout);
  demoTimeouts.length = 0;
  const body = document.getElementById("demo-body");
  if (!body) return;
  const t = I18N[LANG];

  body.innerHTML = `
    <div class="t-line"><span class="t-prompt">❯ </span><span class="t-user" id="d-q"></span><span class="t-cursor" id="d-cur"></span></div>
    <div id="d-rest"></div>`;

  const q = document.getElementById("d-q");
  const rest = document.getElementById("d-rest");

  later(() => typeText(q, t.term_q, 34, () => {
    document.getElementById("d-cur").style.display = "none";

    later(() => {
      rest.insertAdjacentHTML("beforeend", `
        <div class="t-sql fade-in"><span class="t-kw">WITH</span> ventas_mes <span class="t-kw">AS</span> (
  <span class="t-kw">SELECT</span> FORMAT(fecha, 'yyyy-MM') mes, sucursal,
         <span class="t-kw">SUM</span>(importe) total
  <span class="t-kw">FROM</span> ventas
  <span class="t-kw">WHERE</span> fecha &gt;= '2026-01-01'
  <span class="t-kw">GROUP BY</span> FORMAT(fecha, 'yyyy-MM'), sucursal
)
<span class="t-kw">SELECT</span> * <span class="t-kw">FROM</span> ventas_mes <span class="t-kw">ORDER BY</span> mes;</div>`);
    }, 350);

    later(() => {
      rest.insertAdjacentHTML("beforeend", `
        <div class="t-conf fade-in">✓ ${t.term_conf}
          <div class="t-conf-bar"><div class="t-conf-fill" id="d-conf"></div></div>
        </div>`);
      requestAnimationFrame(() =>
        requestAnimationFrame(() => { document.getElementById("d-conf").style.width = "92%"; }));
    }, 1300);

    later(() => {
      rest.insertAdjacentHTML("beforeend", `
        <table class="t-table fade-in">
          <tr><th>mes</th><th>sucursal</th><th>total</th></tr>
          <tr><td>2026-01</td><td>Centro</td><td>$ 4.182.300</td></tr>
          <tr><td>2026-02</td><td>Centro</td><td>$ 4.514.900</td></tr>
          <tr><td>2026-03</td><td>Norte</td><td>$ 3.906.150</td></tr>
        </table>
        <div class="t-line" style="color:var(--muted);font-size:.72rem">${t.term_rows}</div>`);
    }, 2100);

    later(() => {
      rest.insertAdjacentHTML("beforeend", `
        <div class="t-chart fade-in" id="d-chart">
          ${[42, 58, 49, 66, 78, 92].map((h) =>
            `<div class="t-bar" data-h="${h}"><span></span></div>`).join("")}
        </div>
        <div class="t-line fade-in" style="font-size:.75rem;color:var(--txt)">${t.term_explain}</div>`);
      requestAnimationFrame(() => requestAnimationFrame(() => {
        document.querySelectorAll("#d-chart .t-bar").forEach((b, i) => {
          demoTimeouts.push(setTimeout(() => { b.style.height = b.dataset.h + "%"; }, i * 90));
        });
      }));
    }, 2800);

    later(restartDemo, 9500); // loop
  }), 700);
}

// ── reveal on scroll ─────────────────────────────────
function setupReveal() {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("fade-in"); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll(".card, .step, .plan, .dl-card").forEach((el) => io.observe(el));
}

// ── init ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".lang-switch button").forEach((b) =>
    b.addEventListener("click", () => applyLang(b.dataset.lang)));
  document.querySelectorAll(".pricing-toggle button").forEach((b) =>
    b.addEventListener("click", () => setPricingMode(b.dataset.mode)));
  applyLang(LANG);
  setPricingMode("sub");
  setupReveal();
});
