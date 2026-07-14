// MV SQL NLP — conector universal de bases (proceso principal)
// Motores: sqlite (better-sqlite3), sqlserver (mssql), mysql (mysql2), postgres (pg)
// Toda conexión es de solo lectura a nivel de uso: run() solo acepta SELECT/WITH
// (la validación fuerte está en engine.assertReadOnly).

let current = null; // { motor, exec(sql), close(), dialect }

const DIALECTS = {
  sqlite: "SQLite",
  sqlserver: "SQL Server (T-SQL)",
  mysql: "MySQL",
  postgres: "PostgreSQL",
};

function dialect() {
  return current ? DIALECTS[current.motor] : "SQLite";
}

async function connect(cfg) {
  await close();
  const { motor } = cfg;

  if (motor === "sqlite") {
    let Database;
    try {
      Database = require("better-sqlite3");
    } catch {
      throw new Error(
        "SQLite no está disponible en este build. Este paquete de Windows se generó sin " +
        "compilar el módulo nativo de SQLite — usá SQL Server, MySQL o PostgreSQL, o " +
        "compilalo vos: abrí una terminal en la carpeta de la app y corré 'npm rebuild'."
      );
    }
    const conn = new Database(cfg.ruta, { readonly: true, fileMustExist: true });
    current = {
      motor,
      exec: async (sql) => {
        const stmt = conn.prepare(sql);
        const rows = stmt.all();
        const columns = stmt.columns().map((c) => c.name);
        return { columns, rows: rows.map((r) => columns.map((c) => r[c])) };
      },
      close: async () => conn.close(),
    };
    return extractCatalogSqlite(conn);
  }

  if (motor === "sqlserver") {
    const mssqlLib = require("mssql");
    const pool = await mssqlLib.connect({
      server: cfg.servidor,
      port: cfg.puerto ? Number(cfg.puerto) : 1433,
      database: cfg.base,
      user: cfg.usuario,
      password: cfg.password,
      options: { trustServerCertificate: true, encrypt: false },
      connectionTimeout: 30000,
    });
    current = {
      motor,
      exec: async (sql) => {
        const r = await pool.request().query(sql);
        const columns = Object.keys(r.recordset.columns || (r.recordset[0] || {}));
        return { columns, rows: r.recordset.map((row) => columns.map((c) => row[c])) };
      },
      close: async () => pool.close(),
    };
    return extractCatalogGeneric(mssqlQueries(), (q) =>
      pool.request().query(q).then((r) => r.recordset.map(Object.values)));
  }

  if (motor === "mysql") {
    const mysql = require("mysql2/promise");
    const conn = await mysql.createConnection({
      host: cfg.servidor, port: cfg.puerto ? Number(cfg.puerto) : 3306,
      database: cfg.base, user: cfg.usuario, password: cfg.password,
    });
    current = {
      motor,
      exec: async (sql) => {
        const [rows, fields] = await conn.query(sql);
        const columns = fields.map((f) => f.name);
        return { columns, rows: rows.map((r) => columns.map((c) => r[c])) };
      },
      close: async () => conn.end(),
    };
    return extractCatalogGeneric(mysqlQueries(cfg.base), async (q, params) => {
      const [rows] = await conn.query(q, params);
      return rows.map(Object.values);
    });
  }

  if (motor === "postgres") {
    const { Client } = require("pg");
    const client = new Client({
      host: cfg.servidor, port: cfg.puerto ? Number(cfg.puerto) : 5432,
      database: cfg.base, user: cfg.usuario, password: cfg.password,
      connectionTimeoutMillis: 30000,
    });
    await client.connect();
    await client.query("SET default_transaction_read_only = on");
    current = {
      motor,
      exec: async (sql) => {
        const r = await client.query(sql);
        const columns = r.fields.map((f) => f.name);
        return { columns, rows: r.rows.map((row) => columns.map((c) => row[c])) };
      },
      close: async () => client.end(),
    };
    return extractCatalogGeneric(pgQueries(), (q) =>
      client.query(q).then((r) => r.rows.map(Object.values)));
  }

  throw new Error(`Motor no soportado: ${motor}`);
}

async function close() {
  if (current) { try { await current.close(); } catch { /* ya cerrada */ } current = null; }
}

async function run(sql, limit = 5000) {
  if (!current) throw new Error("No hay base de datos conectada.");
  sql = applyLimit(sql, current.motor, limit);
  const t0 = Date.now();
  const { columns, rows } = await current.exec(sql);
  return { columns, rows, sql, ms: Date.now() - t0 };
}

function applyLimit(sql, motor, limit) {
  const s = sql.toLowerCase();
  if (motor === "sqlserver") {
    if (!/\btop\s+\d+/.test(s) && !/\boffset\b/.test(s) && !/\bfetch\b/.test(s)) {
      return sql.replace(/^(\s*select\s+)(distinct\s+)?/i,
        (m, sel, dist) => sel + (dist || "") + `TOP ${limit} `);
    }
    return sql;
  }
  if (!/\blimit\s+\d+/.test(s)) return sql.replace(/;?\s*$/, `\nLIMIT ${limit}`);
  return sql;
}

// ── extracción de catálogo ─────────────────────────────────────
function extractCatalogSqlite(conn) {
  const catalog = { tablas: {}, fks: [] };
  const tables = conn.prepare(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
  ).all().map((r) => r.name);

  for (const t of tables) {
    const cols = conn.prepare(`PRAGMA table_info(${JSON.stringify(t)})`).all()
      .map((c) => ({ columna: c.name, tipo: c.type || "TEXT", pk: !!c.pk }));
    let n = null;
    try { n = conn.prepare(`SELECT COUNT(*) c FROM "${t}"`).get().c; } catch { /* vista rota */ }
    catalog.tablas[t] = { columnas: cols, n_filas: n };
    for (const fk of conn.prepare(`PRAGMA foreign_key_list(${JSON.stringify(t)})`).all()) {
      catalog.fks.push({ tabla_origen: t, columna_origen: fk.from, tabla_destino: fk.table, columna_destino: fk.to });
    }
  }
  return catalog;
}

// Ejecuta 3 queries (columnas, pks, fks) y arma el catálogo — para motores de servidor.
async function extractCatalogGeneric(queries, execRows) {
  const catalog = { tablas: {}, fks: [] };
  for (const [tabla, columna, tipo] of await execRows(queries.columns, queries.params)) {
    if (!catalog.tablas[tabla]) catalog.tablas[tabla] = { columnas: [], n_filas: null };
    catalog.tablas[tabla].columnas.push({ columna, tipo, pk: false });
  }
  try {
    for (const [tabla, columna] of await execRows(queries.pks, queries.params)) {
      const t = catalog.tablas[tabla];
      if (t) { const c = t.columnas.find((x) => x.columna === columna); if (c) c.pk = true; }
    }
  } catch { /* sin permisos de metadata: seguimos sin PKs */ }
  try {
    for (const [to, co, td, cd] of await execRows(queries.fks, queries.params)) {
      catalog.fks.push({ tabla_origen: to, columna_origen: co, tabla_destino: td, columna_destino: cd });
    }
  } catch { /* sin FKs declaradas */ }
  return catalog;
}

function mssqlQueries() {
  return {
    columns: `SELECT t.name, c.name, ty.name FROM sys.columns c
      JOIN sys.tables t ON t.object_id=c.object_id
      JOIN sys.types ty ON ty.user_type_id=c.user_type_id ORDER BY t.name, c.column_id`,
    pks: `SELECT t.name, c.name FROM sys.index_columns ic
      JOIN sys.indexes i ON i.object_id=ic.object_id AND i.index_id=ic.index_id AND i.is_primary_key=1
      JOIN sys.tables t ON t.object_id=ic.object_id
      JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id`,
    fks: `SELECT tp.name, cp.name, tr.name, cr.name FROM sys.foreign_keys fk
      JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
      JOIN sys.tables tp ON tp.object_id=fkc.parent_object_id
      JOIN sys.columns cp ON cp.object_id=fkc.parent_object_id AND cp.column_id=fkc.parent_column_id
      JOIN sys.tables tr ON tr.object_id=fkc.referenced_object_id
      JOIN sys.columns cr ON cr.object_id=fkc.referenced_object_id AND cr.column_id=fkc.referenced_column_id`,
  };
}

function mysqlQueries(base) {
  return {
    params: [base],
    columns: `SELECT table_name, column_name, data_type FROM information_schema.columns
      WHERE table_schema = ? ORDER BY table_name, ordinal_position`,
    pks: `SELECT table_name, column_name FROM information_schema.key_column_usage
      WHERE constraint_name = 'PRIMARY' AND table_schema = ?`,
    fks: `SELECT table_name, column_name, referenced_table_name, referenced_column_name
      FROM information_schema.key_column_usage
      WHERE referenced_table_name IS NOT NULL AND table_schema = ?`,
  };
}

function pgQueries() {
  return {
    columns: `SELECT table_name, column_name, data_type FROM information_schema.columns
      WHERE table_schema = 'public' ORDER BY table_name, ordinal_position`,
    pks: `SELECT tc.table_name, kcu.column_name FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
      WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_schema='public'`,
    fks: `SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
      FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
      JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
      WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public'`,
  };
}

module.exports = { connect, close, run, dialect };
