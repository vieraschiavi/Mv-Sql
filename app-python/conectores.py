"""
conectores.py — MV SQL NLP
==================================================================
Conector universal de bases de datos. El objetivo: adaptarse al 100%
de las bases relacionales del cliente sin tocar código.

Motores soportados:
  - SQLite            (archivo local — incluida la demo)
  - SQL Server        (pyodbc, ODBC Driver 17/18)
  - MySQL / MariaDB   (pymysql)
  - PostgreSQL        (psycopg2)

Cada motor implementa la misma interfaz:
  conectar() -> extraer_catalogo() -> ejecutar(sql, limite)
y el resto del sistema (RAG, generación, validador, UI) no cambia.
==================================================================
"""

import re
import sqlite3

from catalogo import extraer_catalogo_sqlite, extraer_catalogo_mssql

MOTORES = {
    "sqlite":    {"nombre": "SQLite (archivo)",   "dialecto": "SQLite"},
    "sqlserver": {"nombre": "SQL Server",         "dialecto": "SQL Server (T-SQL)"},
    "mysql":     {"nombre": "MySQL / MariaDB",    "dialecto": "MySQL"},
    "postgres":  {"nombre": "PostgreSQL",         "dialecto": "PostgreSQL"},
}


class ConexionBD:
    """Conexión + catálogo + ejecución segura, para cualquier motor soportado."""

    def __init__(self, motor, ruta=None, servidor=None, puerto=None,
                 base=None, usuario=None, password=None, driver=None):
        self.motor = motor
        self.dialecto = MOTORES[motor]["dialecto"]
        self.ruta = ruta
        self.params = dict(servidor=servidor, puerto=puerto, base=base,
                           usuario=usuario, password=password, driver=driver)
        self._con = None

    # ── conexión ──────────────────────────────────────────────
    def conectar(self):
        p = self.params
        if self.motor == "sqlite":
            self._con = sqlite3.connect(self.ruta, check_same_thread=False)
        elif self.motor == "sqlserver":
            import pyodbc
            driver = p["driver"] or "ODBC Driver 17 for SQL Server"
            servidor = p["servidor"] + (f",{p['puerto']}" if p.get("puerto") else "")
            cadena = (f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={p['base']};"
                      f"UID={p['usuario']};PWD={p['password']};"
                      f"TrustServerCertificate=yes;Connection Timeout=30;")
            self._con = pyodbc.connect(cadena, readonly=True)
        elif self.motor == "mysql":
            import pymysql
            self._con = pymysql.connect(
                host=p["servidor"], port=int(p.get("puerto") or 3306),
                database=p["base"], user=p["usuario"], password=p["password"],
                connect_timeout=30, read_timeout=120)
        elif self.motor == "postgres":
            import psycopg2
            self._con = psycopg2.connect(
                host=p["servidor"], port=int(p.get("puerto") or 5432),
                dbname=p["base"], user=p["usuario"], password=p["password"],
                connect_timeout=30)
            self._con.set_session(readonly=True)
        else:
            raise ValueError(f"Motor no soportado: {self.motor}")
        return self

    def cerrar(self):
        if self._con is not None:
            try:
                self._con.close()
            finally:
                self._con = None

    # ── catálogo ──────────────────────────────────────────────
    def extraer_catalogo(self):
        if self.motor == "sqlite":
            return extraer_catalogo_sqlite(self.ruta)
        if self.motor == "sqlserver":
            return extraer_catalogo_mssql(self._con)
        if self.motor in ("mysql", "postgres"):
            return _extraer_catalogo_information_schema(self._con, self.motor,
                                                        self.params.get("base"))
        raise ValueError(self.motor)

    # ── ejecución segura ──────────────────────────────────────
    def ejecutar(self, sql, limite=5000):
        """Ejecuta un SELECT y devuelve (columnas, filas, sql_ejecutado)."""
        sql = _aplicar_limite(sql, self.dialecto, limite)
        if self.motor == "sqlite":
            cur = self._con.cursor()
        else:
            cur = self._con.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        filas = [tuple(r) for r in cur.fetchall()]
        if self.motor == "postgres":
            self._con.rollback()  # cerrar la transacción read-only
        return cols, filas, sql


def _aplicar_limite(sql, dialecto, limite):
    """Fuerza un tope de filas si la consulta no lo trae."""
    s = sql.lower()
    if "sql server" in dialecto.lower():
        if " top " not in s and "offset " not in s and "fetch " not in s:
            sql = re.sub(r"(?i)^(\s*select\s+)(distinct\s+)?",
                         lambda m: m.group(1) + (m.group(2) or "") + f"TOP {limite} ",
                         sql, count=1)
    else:
        if not re.search(r"\blimit\s+\d+", s):
            sql = sql.rstrip("; \n") + f"\nLIMIT {limite}"
    return sql


def _extraer_catalogo_information_schema(con, motor, base):
    """Catálogo genérico vía INFORMATION_SCHEMA (MySQL y PostgreSQL)."""
    cur = con.cursor()
    catalogo = {"tablas": {}, "fks": [], "joins_inferidos": {}}

    if motor == "mysql":
        filtro_schema, param = "table_schema = %s", (base,)
        q_fks = """
            SELECT table_name, column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE referenced_table_name IS NOT NULL AND table_schema = %s"""
    else:  # postgres
        filtro_schema, param = "table_schema = 'public'", ()
        q_fks = """
            SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'"""

    cur.execute(f"""
        SELECT table_name, column_name, data_type,
               CASE WHEN is_nullable = 'YES' THEN 1 ELSE 0 END
        FROM information_schema.columns
        WHERE {filtro_schema}
        ORDER BY table_name, ordinal_position""", param)
    columnas_por_tabla = {}
    for tabla, columna, tipo, nullable in cur.fetchall():
        catalogo["tablas"].setdefault(tabla, {"columnas": [], "n_filas": None, "muestras": {}})
        catalogo["tablas"][tabla]["columnas"].append(
            {"columna": columna, "tipo": tipo, "nullable": bool(nullable), "pk": False})
        columnas_por_tabla.setdefault(tabla, []).append(columna)

    # PKs
    if motor == "mysql":
        cur.execute("""
            SELECT table_name, column_name FROM information_schema.key_column_usage
            WHERE constraint_name = 'PRIMARY' AND table_schema = %s""", (base,))
    else:
        cur.execute("""
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public'""")
    pks = set(cur.fetchall())
    for tabla, info in catalogo["tablas"].items():
        for c in info["columnas"]:
            if (tabla, c["columna"]) in pks:
                c["pk"] = True

    # conteo de filas (aproximado, barato)
    try:
        if motor == "mysql":
            cur.execute("""SELECT table_name, table_rows FROM information_schema.tables
                           WHERE table_schema = %s""", (base,))
        else:
            cur.execute("""SELECT relname, reltuples::bigint FROM pg_class c
                           JOIN pg_namespace n ON n.oid = c.relnamespace
                           WHERE n.nspname = 'public' AND c.relkind = 'r'""")
        for tabla, filas in cur.fetchall():
            if tabla in catalogo["tablas"]:
                catalogo["tablas"][tabla]["n_filas"] = int(filas or 0)
    except Exception:
        pass

    # FKs
    cur.execute(q_fks, param if motor == "mysql" else ())
    for to_, co, td, cd in cur.fetchall():
        catalogo["fks"].append({"tabla_origen": to_, "columna_origen": co,
                                "tabla_destino": td, "columna_destino": cd})

    # joins inferidos por nombre
    col_a_tablas = {}
    for t, cols in columnas_por_tabla.items():
        for c in cols:
            if c.lower().endswith("_id") or c.lower().startswith("id"):
                col_a_tablas.setdefault(c, []).append(t)
    catalogo["joins_inferidos"] = {c: ts for c, ts in col_a_tablas.items() if len(ts) > 1}

    if motor == "postgres":
        con.rollback()
    return catalogo
