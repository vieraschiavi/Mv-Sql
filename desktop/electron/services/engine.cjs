// MV SQL NLP — motor NL2SQL (retrieval + generación + validación + confianza)
const { complete } = require("./ai.cjs");

let CATALOG = null;
let DIALECT = "SQLite";
let CARDS = [];

function setCatalog(catalog, dialect) {
  CATALOG = catalog;
  DIALECT = dialect;
  CARDS = buildCards(catalog);
}

// ── fichas de tabla + retrieval liviano (overlap de tokens) ───
function buildCards(catalog) {
  return Object.entries(catalog.tablas).map(([tabla, info]) => {
    const lines = [`TABLA: ${tabla}`];
    if (info.n_filas != null) lines.push(`Filas: ${info.n_filas}`);
    lines.push("Columnas:");
    for (const c of info.columnas) lines.push(`  - ${c.columna} (${c.tipo})${c.pk ? " [PK]" : ""}`);
    const rels = catalog.fks
      .filter((fk) => fk.tabla_origen === tabla || fk.tabla_destino === tabla)
      .map((fk) => `  ${fk.tabla_origen}.${fk.columna_origen} -> ${fk.tabla_destino}.${fk.columna_destino}`);
    if (rels.length) lines.push("Relaciones (JOINs):", ...rels);
    return { tabla, texto: lines.join("\n") };
  });
}

function tokens(s) {
  return (s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .match(/[a-z_][a-z0-9_]*/g) || []);
}

function retrieve(question, k = 4) {
  const q = new Set(tokens(question));
  const scored = CARDS.map((c) => {
    const t = tokens(c.texto);
    let hits = 0;
    for (const w of new Set(t)) {
      // coincidencia exacta o por prefijo (cliente ~ clientes, cobro ~ cobranza)
      for (const qw of q) {
        if (w === qw || (qw.length > 3 && w.startsWith(qw)) || (w.length > 3 && qw.startsWith(w))) { hits++; break; }
      }
    }
    return { card: c, score: hits / Math.sqrt(t.length + 1) };
  }).sort((a, b) => b.score - a.score);
  const top = scored.slice(0, Math.max(k, 3));
  return { cards: top.map((s) => s.card), simTop: top[0]?.score ?? 0 };
}

// ── prompts ───────────────────────────────────────────────────
const SYSTEM_SQL = (dialect, schema) => `Sos un experto en SQL que traduce preguntas en lenguaje natural a consultas SQL profesionales. La pregunta puede venir en español, inglés o portugués.

REGLAS ESTRICTAS:
1. Usá EXCLUSIVAMENTE las tablas y columnas del esquema provisto. NUNCA inventes nombres.
2. El motor es ${dialect}. Usá exactamente su sintaxis.
3. OPTIMIZACIÓN: estructurá con CTEs (WITH ... AS) los pasos lógicos; evitá SELECT *; filtrá temprano; nunca apliques funciones sobre columnas en el WHERE — usá rangos.
4. Ranking o "top": ORDER BY + límite de filas.
5. JOINs explícitos según las relaciones del esquema.
6. Filtrá registros anulados/eliminados si existe la columna.
7. Solo SELECT (o WITH...SELECT). Nunca INSERT/UPDATE/DELETE/DROP/ALTER/EXEC.
8. Alias legibles para columnas calculadas.

FORMATO DE RESPUESTA — devolvé EXACTAMENTE esto, sin markdown:
SQL:
<la consulta>
CONFIANZA: <entero 0-100>
SUPUESTOS: <supuestos en una línea, o "ninguno">

ESQUEMA DISPONIBLE (usá solo esto):
${schema}`;

const SYSTEM_EXPLAIN = `Sos un analista de datos. Te paso una pregunta, el SQL ejecutado y una muestra del resultado. Explicá el resultado en 2-4 frases claras en el MISMO idioma de la pregunta, con números concretos. No expliques el SQL. Si está vacío, decilo y sugerí por qué.`;

// ── parseo / validación / confianza ───────────────────────────
function parseResponse(text) {
  text = text.replace(/```sql|```/gi, "").trim();
  const conf = text.match(/CONFIANZA:\s*(\d{1,3})/)?.[1];
  const assumptions = text.match(/SUPUESTOS:\s*(.+)/)?.[1]?.trim() ?? "";
  let sql = text.match(/SQL:\s*([\s\S]*?)(?:CONFIANZA:|$)/)?.[1]?.trim()
    ?? text.split(/CONFIANZA:/)[0].trim();
  return { sql, confLLM: conf != null ? Math.min(100, +conf) : null, assumptions };
}

const FORBIDDEN = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ",
  "create ", "exec ", "execute ", "merge ", "grant ", "revoke ", "xp_"];
const SQL_WORDS = new Set(["select", "where", "group", "order", "having", "limit",
  "offset", "union", "unnest", "generate_series", "dual", "values", "lateral"]);

function assertReadOnly(sql) {
  const s = sql.toLowerCase();
  for (const w of FORBIDDEN) if (s.includes(w)) throw new Error(`Operación no permitida: '${w.trim()}' — MV SQL NLP es solo lectura.`);
  const start = s.trimStart().slice(0, 8);
  if (!start.startsWith("select") && !start.startsWith("with")) {
    throw new Error("Solo se permiten consultas SELECT (o WITH...SELECT).");
  }
}

function validate(sql, catalog) {
  const problems = [], warnings = [];
  const s = sql.toLowerCase();
  try { assertReadOnly(sql); } catch (e) { problems.push(e.message); }

  const cteNames = new Set([...s.matchAll(/(?:with|,)\s*([a-z_][a-z0-9_]*)\s+as\s*\(/g)].map((m) => m[1]));
  const catTables = new Set(Object.keys(catalog.tablas).map((t) => t.toLowerCase()));
  for (const m of s.matchAll(/(?:from|join)\s+\[?([a-z_][a-z0-9_.]*)\]?/g)) {
    const t = m[1].split(".").pop();
    if (!SQL_WORDS.has(t) && !cteNames.has(t) && !catTables.has(t)) {
      problems.push(`Tabla inexistente en el catálogo: '${m[1]}'`);
    }
  }

  const catCols = new Set();
  for (const info of Object.values(catalog.tablas))
    for (const c of info.columnas) catCols.add(c.columna.toLowerCase());
  for (const m of new Set([...s.matchAll(/[a-z_][a-z0-9_]*\.([a-z_][a-z0-9_]*)/g)].map((x) => x[1]))) {
    if (!catCols.has(m) && !SQL_WORDS.has(m)) warnings.push(`Columna no reconocida: '${m}' (puede ser alias de CTE)`);
  }
  return { valid: problems.length === 0, problems, warnings };
}

function confidence(confLLM, simRag, valid, nWarnings, usesCte) {
  const base = confLLM ?? 60;
  const ragSignal = Math.min(1, simRag * 3) * 100;
  const valSignal = Math.max(0, (valid ? 100 : 20) - Math.min(30, nWarnings * 10));
  let score = 0.55 * base + 0.25 * ragSignal + 0.2 * valSignal;
  if (usesCte) score = Math.min(100, score + 2);
  let margin = 5;
  if (confLLM == null) margin += 7;
  if (simRag < 0.05) margin += 5;
  if (nWarnings) margin += 3;
  score = Math.round(Math.max(5, Math.min(99, score)));
  return {
    puntaje: score, margen: margin,
    intervalo: [Math.max(0, score - margin), Math.min(100, score + margin)],
    componentes: { modelo: Math.round(base), rag: Math.round(ragSignal), validacion: Math.round(valSignal) },
  };
}

// ── pipeline principal ────────────────────────────────────────
async function answer(question, ai, { run, k = 4, limit = 5000, explain = true }) {
  if (!CATALOG) throw new Error("Conectá una base de datos primero.");
  const { cards, simTop } = retrieve(question, k);
  const schema = cards.map((c) => c.texto).join("\n\n");
  const system = SYSTEM_SQL(DIALECT, schema);

  let { sql, confLLM, assumptions } = parseResponse(await complete(ai, system, question));
  let { valid, problems, warnings } = validate(sql, CATALOG);

  // self-repair: un reintento con los errores del validador
  if (!valid) {
    try {
      const fix = `${question}\n\nTu consulta anterior fue:\n${sql}\n\nFue RECHAZADA por:\n- ${problems.join("\n- ")}\nGenerá una consulta corregida usando SOLO tablas y columnas del esquema.`;
      const retry = parseResponse(await complete(ai, system, fix));
      const revalid = validate(retry.sql, CATALOG);
      if (revalid.valid) {
        ({ sql, confLLM, assumptions } = retry);
        ({ valid, problems, warnings } = revalid);
      }
    } catch { /* reintento best-effort */ }
  }

  const usesCte = sql.trimStart().toLowerCase().startsWith("with");
  const result = {
    pregunta: question, tablas: cards.map((c) => c.tabla), sql, valido: valid,
    problemas: problems, advertencias: warnings, supuestos: assumptions,
    confianza: confidence(confLLM, simTop, valid, warnings.length, usesCte),
    columnas: null, filas: null, sqlEjecutado: null, ms: null, error: null, explicacion: null,
  };

  if (valid) {
    try {
      const r = await run(sql, limit);
      Object.assign(result, { columnas: r.columns, filas: r.rows, sqlEjecutado: r.sql, ms: r.ms });
    } catch (e) { result.error = e.message; }
  }

  if (explain && result.filas) {
    try {
      const sample = [result.columnas.join(" | "),
        ...result.filas.slice(0, 20).map((f) => f.join(" | "))].join("\n");
      result.explicacion = await complete(ai, SYSTEM_EXPLAIN,
        `PREGUNTA: ${question}\n\nSQL:\n${sql}\n\nRESULTADO (${result.filas.length} filas):\n${sample}`, 400);
    } catch { /* la explicación es opcional */ }
  }
  return result;
}

async function storedProcedure(sql, name, ai) {
  const system = `Sos un DBA experto. Convertí la consulta SELECT en un STORED PROCEDURE de producción para ${DIALECT}, llamado ${name}. Parametrizá fechas y filtros literales con defaults sensatos. Incluí comentario de cabecera. Devolvé SOLO el código SQL, sin markdown.`;
  return (await complete(ai, system, sql, 2000)).replace(/```sql|```/gi, "").trim();
}

async function optimize(sql, ai) {
  const system = `Sos un optimizador de SQL para ${DIALECT}. Reescribí la consulta con CTEs donde aporten, sin SELECT *, filtrando temprano. Mantené la misma semántica. Devolvé el SQL optimizado y una línea final 'CAMBIOS: ...'.`;
  return complete(ai, system, sql, 2000);
}

async function testProvider(ai) {
  try {
    const txt = await complete(ai, "Respondé solo con la palabra OK.", "ping", 10);
    return { ok: true, message: `Conexión OK — ${txt.trim().slice(0, 40)}` };
  } catch (e) { return { ok: false, message: e.message }; }
}

module.exports = { setCatalog, answer, storedProcedure, optimize, testProvider, assertReadOnly };
