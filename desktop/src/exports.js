// MV SQL NLP — exportaciones (renderer): Excel, CSV, PDF, HTML
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

function toBase64(u8) {
  let bin = "";
  const CHUNK = 0x8000;
  for (let i = 0; i < u8.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, u8.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

async function save(defaultName, u8, ext, name) {
  return window.mvsql.saveFile({
    defaultName,
    dataBase64: toBase64(u8),
    filters: [{ name, extensions: [ext] }],
  });
}

export async function exportExcel(columns, rows, sql) {
  const ws = XLSX.utils.aoa_to_sheet([columns, ...rows]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Resultado");
  const meta = XLSX.utils.aoa_to_sheet([
    ["Generado por", "MV SQL NLP"],
    ["Fecha", new Date().toLocaleString()],
    ["Filas", rows.length],
    ["SQL", (sql || "").slice(0, 1000)],
  ]);
  XLSX.utils.book_append_sheet(wb, meta, "Info");
  const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return save("mvsql_resultado.xlsx", new Uint8Array(out), "xlsx", "Excel");
}

export async function exportCsv(columns, rows) {
  const esc = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = "﻿" + [columns, ...rows].map((r) => r.map(esc).join(",")).join("\n");
  return save("mvsql_resultado.csv", new TextEncoder().encode(csv), "csv", "CSV");
}

export async function exportPdf(columns, rows, { pregunta = "", sql = "", explicacion = "" } = {}) {
  const doc = new jsPDF({ orientation: columns.length > 6 ? "landscape" : "portrait" });
  doc.setFontSize(16);
  doc.setTextColor(30, 58, 138);
  doc.text("MV SQL NLP — Resultado de consulta", 14, 16);
  doc.setFontSize(9);
  doc.setTextColor(70);
  let y = 24;
  if (pregunta) { doc.text(doc.splitTextToSize(`Pregunta: ${pregunta}`, 260), 14, y); y += 6; }
  if (explicacion) {
    const lines = doc.splitTextToSize(`Análisis: ${explicacion}`, 260);
    doc.text(lines, 14, y); y += lines.length * 4 + 2;
  }
  doc.setTextColor(120);
  doc.text(`${new Date().toLocaleString()} · ${rows.length} filas`, 14, y); y += 4;
  autoTable(doc, {
    startY: y + 2,
    head: [columns],
    body: rows.slice(0, 300).map((r) => r.map((v) => (v == null ? "" : String(v)))),
    styles: { fontSize: 7 },
    headStyles: { fillColor: [30, 58, 138] },
    alternateRowStyles: { fillColor: [241, 245, 249] },
  });
  if (sql) {
    const yEnd = (doc.lastAutoTable?.finalY ?? y) + 8;
    doc.setFontSize(7);
    doc.setTextColor(90);
    doc.text(doc.splitTextToSize(`SQL: ${sql}`, 260), 14, yEnd);
  }
  const u8 = new Uint8Array(doc.output("arraybuffer"));
  return save("mvsql_resultado.pdf", u8, "pdf", "PDF");
}

export async function exportHtml(columns, rows) {
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>MV SQL NLP</title>
<style>body{font-family:system-ui;margin:2rem;color:#0f172a}h1{color:#1e3a8a}
table{border-collapse:collapse;width:100%}th{background:#1e3a8a;color:#fff;padding:.5rem;text-align:left}
td{padding:.4rem .5rem;border-bottom:1px solid #e2e8f0}tr:nth-child(even) td{background:#f8fafc}</style>
</head><body><h1>MV SQL NLP</h1><table><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr>
${rows.map((r) => `<tr>${r.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</table></body></html>`;
  return save("mvsql_resultado.html", new TextEncoder().encode(html), "html", "HTML");
}
