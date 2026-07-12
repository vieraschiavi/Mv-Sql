import React, { useMemo, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  PieChart, Pie, Cell, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { exportExcel, exportCsv, exportPdf, exportHtml } from "../exports.js";

const COLORS = ["#38bdf8", "#818cf8", "#c084fc", "#34d399", "#fbbf24", "#f87171"];

function Confidence({ conf, t }) {
  if (!conf) return null;
  const [lo, hi] = conf.intervalo;
  return (
    <div>
      <b>{t.confidence}: {conf.puntaje}% <span style={{ color: "var(--muted)" }}>
        (±{conf.margen} → {lo}–{hi}%)</span></b>
      <div className="conf-bar-bg">
        <div className="conf-bar" style={{ width: `${conf.puntaje}%` }} />
        <div className="conf-interval" style={{ left: `${lo}%`, width: `${hi - lo}%` }} />
      </div>
      <div className="conf-comp">
        modelo {conf.componentes.modelo} · RAG {conf.componentes.rag} · validación {conf.componentes.validacion}
      </div>
    </div>
  );
}

function AutoChart({ columns, rows, t }) {
  const data = useMemo(
    () => rows.slice(0, 300).map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]]))),
    [columns, rows]);
  const numCols = columns.filter((c) => data.length && typeof data[0][c] === "number");
  const catCols = columns.filter((c) => !numCols.includes(c));
  const dateCol = columns.find((c) =>
    /fecha|mes|periodo|dia|anio|año|date|month|data/i.test(c));

  if (!data.length) return <p style={{ color: "var(--muted)" }}>{t.no_chart}</p>;

  const axis = { stroke: "#8fa3bf", fontSize: 11 };
  const grid = <CartesianGrid strokeDasharray="3 3" stroke="#1e2c47" />;
  const tip = <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e2c47" }} />;

  if (dateCol && numCols.length) {
    return (
      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={data}>{grid}
          <XAxis dataKey={dateCol} {...axis} /><YAxis {...axis} />{tip}
          <Line type="monotone" dataKey={numCols[0]} stroke="#38bdf8" strokeWidth={2} dot />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (catCols.length && numCols.length && data.length <= 40) {
    return (
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={[...data].sort((a, b) => b[numCols[0]] - a[numCols[0]])}>{grid}
          <XAxis dataKey={catCols[0]} {...axis} /><YAxis {...axis} />{tip}
          <Bar dataKey={numCols[0]} fill="#818cf8" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  if (numCols.length >= 2) {
    return (
      <ResponsiveContainer width="100%" height={340}>
        <ScatterChart>{grid}
          <XAxis dataKey={numCols[0]} {...axis} name={numCols[0]} />
          <YAxis dataKey={numCols[1]} {...axis} name={numCols[1]} />{tip}
          <Scatter data={data} fill="#c084fc" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }
  if (catCols.length) {
    const counts = {};
    data.forEach((d) => { counts[d[catCols[0]]] = (counts[d[catCols[0]]] || 0) + 1; });
    const pie = Object.entries(counts).map(([name, value]) => ({ name, value }));
    if (pie.length <= 10) {
      return (
        <ResponsiveContainer width="100%" height={340}>
          <PieChart>{tip}
            <Pie data={pie} dataKey="value" nameKey="name" label>
              {pie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      );
    }
  }
  return <p style={{ color: "var(--muted)" }}>{t.no_chart}</p>;
}

export default function Results({ r, t, onSave, onStoredProcedure, onOptimize }) {
  const [tab, setTab] = useState("table");
  const [modal, setModal] = useState(null);       // { title, body }
  const [saveName, setSaveName] = useState("");
  const [savedPath, setSavedPath] = useState(null);
  const [busyAction, setBusyAction] = useState(null);

  if (!r) return null;
  const hasData = r.columnas && r.filas;

  async function doExport(kind) {
    const opts = { pregunta: r.pregunta, sql: r.sqlEjecutado || r.sql, explicacion: r.explicacion || "" };
    const fns = { excel: exportExcel, csv: exportCsv, pdf: exportPdf, html: exportHtml };
    const p = kind === "pdf"
      ? await fns[kind](r.columnas, r.filas, opts)
      : await fns[kind](r.columnas, r.filas, opts.sql);
    if (p) setSavedPath(p);
  }

  async function runAction(kind) {
    setBusyAction(kind);
    try {
      if (kind === "sp") {
        const code = await onStoredProcedure(r.sql, saveName || "sp_mvsql_reporte");
        setModal({ title: "Stored procedure", body: code });
      } else if (kind === "opt") {
        const code = await onOptimize(r.sql);
        setModal({ title: t.optimize, body: code });
      }
    } catch (e) {
      setModal({ title: "Error", body: e.message });
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div>
      <div className="result-grid">
        <div className="card">
          <h4>🧾 {t.sql_gen}</h4>
          <div className="chips" style={{ marginBottom: ".6rem" }}>
            {r.tablas.map((tb) => <span className="chip" key={tb}>{tb}</span>)}
          </div>
          <pre className="sql">{r.sql}</pre>
          {r.valido
            ? <div className="status-ok">✓ {t.validated}</div>
            : (<div className="status-err">✗ {t.invalid} {r.problemas.join(" · ")}</div>)}
          {r.advertencias.length > 0 && (
            <div style={{ color: "var(--amber)", fontSize: ".75rem", marginTop: ".3rem" }}>
              ⚠ {r.advertencias.join(" · ")}
            </div>
          )}
        </div>
        <div className="card">
          <h4>📐 {t.confidence}</h4>
          <Confidence conf={r.confianza} t={t} />
          {r.supuestos && !/^(ninguno|none|nenhum)/i.test(r.supuestos) && (
            <p style={{ color: "var(--muted)", fontSize: ".78rem", marginTop: ".6rem" }}>
              💭 {t.assumptions}: {r.supuestos}
            </p>
          )}
        </div>
      </div>

      {r.error && <div className="card status-err" style={{ marginBottom: "1rem" }}>{r.error}</div>}

      {hasData && (
        <div className="card">
          <div className="metrics">
            <div className="metric"><b>{r.filas.length.toLocaleString()}</b><span>{t.rows}</span></div>
            <div className="metric"><b>{r.columnas.length}</b><span>{t.result}</span></div>
            {r.ms != null && <div className="metric"><b>{(r.ms / 1000).toFixed(1)}s</b><span>⏱</span></div>}
          </div>

          <div className="tabs">
            {["table", "chart", "analysis"].map((k) => (
              <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>
                {k === "table" ? `📋 ${t.table}` : k === "chart" ? `📈 ${t.chart}` : `🧠 ${t.analysis}`}
              </button>
            ))}
          </div>

          {tab === "table" && (
            <div className="tbl-wrap">
              <table className="result">
                <thead><tr>{r.columnas.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {r.filas.slice(0, 1000).map((row, i) => (
                    <tr key={i}>{row.map((v, j) => <td key={j}>{v == null ? "" : String(v)}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {tab === "chart" && <AutoChart columns={r.columnas} rows={r.filas} t={t} />}
          {tab === "analysis" && <p style={{ lineHeight: 1.7 }}>{r.explicacion || "—"}</p>}

          <div className="actions">
            <button className="ghost small" onClick={() => doExport("excel")}>⬇ Excel</button>
            <button className="ghost small" onClick={() => doExport("csv")}>⬇ CSV</button>
            <button className="ghost small" onClick={() => doExport("pdf")}>⬇ PDF</button>
            <button className="ghost small" onClick={() => doExport("html")}>⬇ HTML</button>
            <span style={{ flex: 1 }} />
            <input style={{ width: 190 }} placeholder={t.query_name} value={saveName}
                   onChange={(e) => setSaveName(e.target.value)} />
            <button className="small" onClick={() => saveName && onSave(saveName)}>⭐ {t.save_query}</button>
            <button className="ghost small" disabled={busyAction === "sp"} onClick={() => runAction("sp")}>
              🧱 {t.sp}
            </button>
            <button className="ghost small" disabled={busyAction === "opt"} onClick={() => runAction("opt")}>
              🚀 {t.optimize}
            </button>
          </div>
          {savedPath && <div className="status-ok">✓ {t.saved_to}: {savedPath}</div>}
        </div>
      )}

      {modal && (
        <div className="modal-bg" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{modal.title}</h3>
            <pre className="sql">{modal.body}</pre>
            <div className="btn-row">
              <button className="ghost" onClick={() => navigator.clipboard.writeText(modal.body)}>📋 Copy</button>
              <button onClick={() => setModal(null)}>OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
