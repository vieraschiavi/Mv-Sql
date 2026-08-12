# desktop/electron/services/db.cjs

- dialect · function · L19-L21 — function dialect()
- validar · function · L37-L45 — function validar(cfg)
- conectarArchivos · function · L53-L61 — async function conectarArchivos(cfg, Database)
- connect · function · L63-L169 — async function connect(cfg)
- close · function · L171-L173 — async function close()
- run · function · L175-L192 — async function run(sql, limit = 5000)
- applyLimit · function · L194-L205 — function applyLimit(sql, motor, limit)
- extractCatalogSqlite · function · L208-L225 — function extractCatalogSqlite(conn)
- extractCatalogGeneric · function · L228-L246 — async function extractCatalogGeneric(queries, execRows)
- mssqlQueries · function · L248-L264 — function mssqlQueries()
- mysqlQueries · function · L266-L277 — function mysqlQueries(base)
- pgQueries · function · L279-L292 — function pgQueries()
