import React, { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Results from "./components/Results.jsx";
import { I18N, EXAMPLES, PROVIDERS } from "./i18n.js";

export default function App() {
  const [lang, setLang] = useState("es");
  const [ai, setAi] = useState({ provider: "anthropic", apiKey: "", model: "claude-haiku-4-5-20251001", baseUrl: "" });
  const [catalog, setCatalog] = useState(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState([]);
  const [history, setHistory] = useState([]);

  const t = I18N[lang];

  // cargar preferencias + consultas guardadas
  useEffect(() => {
    (async () => {
      const prefs = await window.mvsql.storeGet("prefs");
      if (prefs?.lang) setLang(prefs.lang);
      if (prefs?.ai) setAi((a) => ({ ...a, ...prefs.ai, apiKey: prefs.ai.apiKey || "" }));
      setSaved((await window.mvsql.storeGet("saved")) || []);
    })();
  }, []);

  function persistPrefs(nextLang = lang, nextAi = ai) {
    window.mvsql.storeSet("prefs", { lang: nextLang, ai: nextAi });
  }

  async function connect(cfg) {
    const r = await window.mvsql.connect(cfg);
    setCatalog(r.catalog);
    setResult(null);
    return r;
  }

  async function ask(q) {
    const text = (q ?? question).trim();
    if (!text) return;
    setError(null);
    if (!catalog) { setError(t.need_db); return; }
    if (PROVIDERS[ai.provider].needsKey && !ai.apiKey) { setError(t.need_key); return; }
    setBusy(true);
    try {
      const r = await window.mvsql.ask({ question: text, ai, options: {} });
      setResult(r);
      setHistory((h) => [{ pregunta: text, sql: r.sql }, ...h].slice(0, 30));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveQuery(name) {
    const item = { nombre: name, pregunta: result.pregunta, sql: result.sql,
                   fecha: new Date().toISOString() };
    const next = [...saved.filter((s) => s.nombre !== name), item];
    setSaved(next);
    await window.mvsql.storeSet("saved", next);
  }

  async function deleteSaved(name) {
    const next = saved.filter((s) => s.nombre !== name);
    setSaved(next);
    await window.mvsql.storeSet("saved", next);
  }

  async function runSaved(q) {
    setQuestion(q.pregunta || "");
    if (q.pregunta) { await ask(q.pregunta); return; }
    setBusy(true);
    try {
      const r = await window.mvsql.runSql(q.sql);
      setResult({ pregunta: q.nombre, tablas: [], sql: q.sql, valido: true,
                  problemas: [], advertencias: [], supuestos: "", confianza: null,
                  columnas: r.columns, filas: r.rows, sqlEjecutado: r.sql,
                  ms: r.ms, error: null, explicacion: null });
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="layout">
      <Sidebar
        t={t} lang={lang}
        setLang={(l) => { setLang(l); persistPrefs(l, ai); }}
        ai={ai}
        setAi={(a) => { setAi(a); persistPrefs(lang, a); }}
        onConnect={connect} catalog={catalog}
        saved={saved} onRunSaved={runSaved} onDeleteSaved={deleteSaved}
      />
      <main className="main">
        {!catalog && !result ? (
          <div className="welcome">
            <h1>⚡ <span className="grad-text">{t.welcome_t}</span></h1>
            <p>{t.welcome_s}</p>
          </div>
        ) : (
          <>
            <div className="ask-row">
              <input value={question} placeholder={t.ask_ph}
                     onChange={(e) => setQuestion(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && ask()} />
              <button onClick={() => ask()} disabled={busy} style={{ minWidth: 130 }}>
                {busy ? <span className="spinner" /> : "⚡ "}{busy ? t.thinking : t.ask}
              </button>
            </div>
            <div className="examples">
              {EXAMPLES[lang].map((ej) => (
                <button key={ej} onClick={() => { setQuestion(ej); ask(ej); }}>{ej}</button>
              ))}
            </div>
            {error && <div className="card status-err" style={{ marginBottom: "1rem" }}>{error}</div>}
            <Results
              r={result} t={t}
              onSave={saveQuery}
              onStoredProcedure={(sql, name) => window.mvsql.storedProcedure({ sql, name, ai })}
              onOptimize={(sql) => window.mvsql.optimize({ sql, ai })}
            />
            {history.length > 1 && (
              <details className="card" style={{ marginTop: "1rem" }}>
                <summary style={{ cursor: "pointer" }}>🕘 {t.history} ({history.length})</summary>
                {history.map((h, i) => (
                  <div key={i} style={{ margin: ".6rem 0" }}>
                    <b style={{ fontSize: ".85rem" }}>{h.pregunta}</b>
                    <pre className="sql" style={{ marginTop: ".3rem" }}>{h.sql}</pre>
                  </div>
                ))}
              </details>
            )}
          </>
        )}
      </main>
    </div>
  );
}
