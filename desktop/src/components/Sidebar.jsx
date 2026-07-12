import React, { useState } from "react";
import { PROVIDERS, ENGINES } from "../i18n.js";

export default function Sidebar({ t, lang, setLang, ai, setAi, onConnect,
                                  connection, catalog, saved, onRunSaved, onDeleteSaved }) {
  const [motor, setMotor] = useState("sqlite");
  const [ruta, setRuta] = useState("");
  const [srv, setSrv] = useState({ servidor: "", puerto: "", base: "", usuario: "", password: "" });
  const [testMsg, setTestMsg] = useState(null);
  const [connMsg, setConnMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const prov = PROVIDERS[ai.provider];

  async function testAI() {
    setTestMsg({ ok: null, message: "…" });
    setTestMsg(await window.mvsql.testAI(ai));
  }

  async function connect() {
    setBusy(true);
    setConnMsg(null);
    try {
      const cfg = motor === "sqlite" ? { motor, ruta } : { motor, ...srv };
      const r = await onConnect(cfg);
      setConnMsg({ ok: true, message: `✓ ${r.tables} ${t.connected}` });
    } catch (e) {
      setConnMsg({ ok: false, message: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="sidebar">
      <div className="logo">⚡ MV SQL <span className="grad-text">NLP</span></div>

      <div className="lang-row">
        {["es", "en", "pt"].map((l) => (
          <button key={l} className={lang === l ? "active" : ""} onClick={() => setLang(l)}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      {/* ── IA ── */}
      <div className="side-section">
        <h3>🤖 {t.provider}</h3>
        <select value={ai.provider}
                onChange={(e) => setAi({ ...ai, provider: e.target.value, model: PROVIDERS[e.target.value].modelos[0] || "" })}>
          {Object.entries(PROVIDERS).map(([k, p]) => <option key={k} value={k}>{p.nombre}</option>)}
        </select>
        <label>{t.model}</label>
        {prov.modelos.length ? (
          <select value={ai.model} onChange={(e) => setAi({ ...ai, model: e.target.value })}>
            {prov.modelos.map((m) => <option key={m}>{m}</option>)}
          </select>
        ) : (
          <input value={ai.model} placeholder="gpt-4o-mini"
                 onChange={(e) => setAi({ ...ai, model: e.target.value })} />
        )}
        {(ai.provider === "custom" || ai.provider === "ollama") && (
          <>
            <label>Base URL</label>
            <input value={ai.baseUrl || ""} placeholder={ai.provider === "ollama" ? "http://localhost:11434" : "https://api…/v1"}
                   onChange={(e) => setAi({ ...ai, baseUrl: e.target.value })} />
          </>
        )}
        {prov.needsKey && (
          <>
            <label>{t.apikey}</label>
            <input type="password" value={ai.apiKey || ""}
                   onChange={(e) => setAi({ ...ai, apiKey: e.target.value })} />
          </>
        )}
        <div className="btn-row">
          <button className="ghost small" onClick={testAI}>🔌 {t.test}</button>
        </div>
        {testMsg && <div className={testMsg.ok ? "status-ok" : "status-err"}>{testMsg.message}</div>}
      </div>

      {/* ── Base de datos ── */}
      <div className="side-section">
        <h3>🗄️ {t.db}</h3>
        <select value={motor} onChange={(e) => setMotor(e.target.value)}>
          {Object.entries(ENGINES).map(([k, n]) => <option key={k} value={k}>{n}</option>)}
        </select>
        {motor === "sqlite" ? (
          <>
            <label>{t.file}</label>
            <div className="btn-row" style={{ marginTop: 0 }}>
              <input value={ruta} onChange={(e) => setRuta(e.target.value)} placeholder="C:\\datos\\mi_base.db" />
              <button className="ghost small" style={{ flex: "0 0 auto" }}
                      onClick={async () => { const p = await window.mvsql.pickSqlite(); if (p) setRuta(p); }}>
                {t.pick}
              </button>
            </div>
          </>
        ) : (
          <>
            <label>{t.server}</label>
            <input value={srv.servidor} onChange={(e) => setSrv({ ...srv, servidor: e.target.value })} />
            <label>{t.port}</label>
            <input value={srv.puerto} onChange={(e) => setSrv({ ...srv, puerto: e.target.value })} />
            <label>{t.database}</label>
            <input value={srv.base} onChange={(e) => setSrv({ ...srv, base: e.target.value })} />
            <label>{t.user}</label>
            <input value={srv.usuario} onChange={(e) => setSrv({ ...srv, usuario: e.target.value })} />
            <label>{t.password}</label>
            <input type="password" value={srv.password} onChange={(e) => setSrv({ ...srv, password: e.target.value })} />
          </>
        )}
        <div className="btn-row">
          <button onClick={connect} disabled={busy}>{busy ? "…" : `🔗 ${t.connect}`}</button>
        </div>
        {connMsg && <div className={connMsg.ok ? "status-ok" : "status-err"}>{connMsg.message}</div>}
        {catalog && (
          <details style={{ marginTop: ".6rem" }}>
            <summary style={{ cursor: "pointer", fontSize: ".8rem", color: "var(--muted)" }}>
              📚 {t.schema}
            </summary>
            <div className="schema-tables" style={{ marginTop: ".5rem" }}>
              {Object.entries(catalog.tablas).map(([tb, info]) => (
                <div key={tb}>
                  <b>{tb}</b>{info.n_filas != null ? ` · ${info.n_filas.toLocaleString()}` : ""}
                  <p>{info.columnas.map((c) => c.columna).join(", ")}</p>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>

      {/* ── Consultas guardadas ── */}
      <div className="side-section">
        <h3>⭐ {t.saved}</h3>
        {!saved.length && <p style={{ color: "var(--muted)", fontSize: ".78rem" }}>{t.none_saved}</p>}
        {saved.map((q) => (
          <div className="saved-item" key={q.nombre}>
            <b>📌 {q.nombre}</b>
            <span>{q.pregunta}</span>
            <div style={{ display: "flex", gap: ".4rem" }}>
              <button className="ghost small" onClick={() => onRunSaved(q)}>▶ {t.run}</button>
              <button className="ghost small" onClick={() => onDeleteSaved(q.nombre)}>🗑 {t.del}</button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
