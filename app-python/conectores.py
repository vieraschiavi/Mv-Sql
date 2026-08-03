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

import os
import re
import sqlite3
from urllib.request import pathname2url

from catalogo import extraer_catalogo_sqlite, extraer_catalogo_mssql


class SQLNoPermitido(Exception):
    """El SQL que se intentó ejecutar no es de solo lectura."""


# Operaciones que nunca se ejecutan. Se matchean con \b (límite de
# palabra) y no como substring con espacio: "delete " no matchea
# "DELETE\nFROM" ni "DELETE\tFROM", y esa era justamente la forma de
# saltearse el filtro que hacía motor.py.
#
# La lista es deliberadamente corta. Como acá arriba ya se exige un solo
# statement que empiece con SELECT/WITH, lo único que queda por frenar es
# un CTE modificador (WITH x AS (DELETE ... RETURNING) SELECT ...), que es
# el caso real que sí pasa esos dos chequeos. Agregar palabras "por las
# dudas" tiene costo: REPLACE(), por ejemplo, es una función de texto
# legítima en un SELECT, y bloquearla rompería consultas válidas del
# cliente. Por eso REPLACE solo se frena en su forma peligrosa
# (REPLACE INTO), y no se filtran SET/CALL/DO/LOAD, que no pueden
# aparecer como statement con las dos reglas de arriba puestas.
_PROHIBIDAS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|"
    r"exec|execute|merge|grant|revoke|attach|detach|vacuum|reindex|pragma|"
    # 'into' cubre las tres formas de ESCRITURA que arrancan con SELECT y
    # pasarían el prefijo: 'SELECT ... INTO OUTFILE/DUMPFILE' (MySQL escribe
    # un archivo en el server → RCE), 'REPLACE INTO', y 'SELECT ... INTO
    # tabla' (SQL Server/Postgres crean una tabla). Un 'into' dentro de un
    # literal de texto no dispara: los literales se sacan antes de buscar.
    r"into|"
    # Funciones de lectura/escritura del filesystem del server. Son SELECT
    # puros, así que la barrera vieja los dejaba pasar y filtraban /etc/passwd
    # o escribían archivos con las credenciales del cliente.
    r"load_file|outfile|dumpfile|"                       # MySQL
    r"pg_read_file|pg_read_binary_file|pg_ls_dir|lo_export|lo_import|"  # Postgres
    r"openrowset|opendatasource|xp_cmdshell|"            # SQL Server
    r"utl_file|dbms_)"                                   # Oracle (por si acaso)
    r"\b"
    r"|\bxp_|\bsp_executesql",
    re.IGNORECASE,
)

# Los comentarios se sacan antes de mirar el SQL: "DELETE/**/FROM" o un
# "--" que esconda medio statement no deben poder tapar una operación.
_COMENTARIO_BLOQUE = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMENTARIO_LINEA = re.compile(r"--[^\n]*")

# Literal de texto SQL: comilla simple, con '' como comilla escapada adentro.
# Se reemplaza por una cadena vacía ('') ANTES de buscar operaciones y ';':
# así "SELECT ';' AS sep" o "SELECT 'algo into algo'" no disparan la alarma
# (eran falsos positivos), y a la vez nada de lo que un atacante esconda
# DENTRO de un string puede evadir la barrera — no lo mira.
_LITERAL = re.compile(r"'(?:[^']|'')*'")


def _sin_comentarios(sql):
    return _COMENTARIO_LINEA.sub(" ", _COMENTARIO_BLOQUE.sub(" ", sql))


def _sin_literales(sql):
    return _LITERAL.sub("''", sql)


def asegurar_solo_lectura(sql):
    """Barrera de solo-lectura, en el punto de ejecución.

    Antes esto vivía solo en motor.py (el orquestador). Cualquier camino
    que no pasara por ahí — por ejemplo una celda SQL de un cuaderno, que
    se guarda en un JSON local sin validar — llegaba al cursor sin
    control. Ahora la regla se aplica acá, que es por donde pasan todos
    los caminos sin excepción.

    Lanza SQLNoPermitido si el SQL no es una lectura pura.
    """
    if not sql or not sql.strip():
        raise SQLNoPermitido("La consulta está vacía.")

    limpio = _sin_comentarios(sql).strip()
    # Sobre la versión sin literales se buscan ';' y operaciones: un ';' o un
    # 'into' escondido dentro de un string de datos ni ayuda a un atacante ni
    # debe frenar una consulta legítima que solo lo lleva como texto.
    sin_lit = _sin_literales(limpio)

    # Un solo statement: un ";" con algo después es encadenamiento
    # ("SELECT 1; DROP TABLE x"). El ";" final suelto es inofensivo.
    if ";" in sin_lit.rstrip().rstrip(";"):
        raise SQLNoPermitido(
            "No se permite ejecutar varias sentencias en una sola consulta.")

    if not re.match(r"^\s*(select|with)\b", sin_lit, re.IGNORECASE):
        raise SQLNoPermitido(
            "MV SQL NLP es de solo lectura: la consulta debe empezar con "
            "SELECT o WITH.")

    hallada = _PROHIBIDAS.search(sin_lit)
    if hallada:
        raise SQLNoPermitido(
            f"Operación no permitida: '{hallada.group(0).strip()}'. "
            "MV SQL NLP nunca modifica tu base de datos.")

    return True

MOTORES = {
    "sqlite":    {"nombre": "SQLite (archivo)",   "dialecto": "SQLite"},
    "sqlserver": {"nombre": "SQL Server",         "dialecto": "SQL Server (T-SQL)"},
    "mysql":     {"nombre": "MySQL / MariaDB",    "dialecto": "MySQL"},
    "postgres":  {"nombre": "PostgreSQL",         "dialecto": "PostgreSQL"},
}


class ConexionBD:
    """Conexión + catálogo + ejecución segura, para cualquier motor soportado."""

    def __init__(self, motor, ruta=None, servidor=None, puerto=None,
                 base=None, usuario=None, password=None, driver=None,
                 ssh=None):
        """ssh: dict opcional para conectarse a través de un túnel SSH
        {host, puerto, usuario, password | clave_privada}. Sirve cuando la
        base no está expuesta a internet y solo se llega por el servidor
        de la empresa — que es como debería estar siempre."""
        self.motor = motor
        self.dialecto = MOTORES[motor]["dialecto"]
        self.ruta = ruta
        self.params = dict(servidor=servidor, puerto=puerto, base=base,
                           usuario=usuario, password=password, driver=driver)
        self.ssh = ssh or None
        self._tunel = None
        self._con = None

    # ── túnel SSH (opcional) ──────────────────────────────────
    def _abrir_tunel(self):
        """Levanta el túnel y reapunta host/puerto al extremo local.

        Requiere `pip install sshtunnel`. Si no está instalado se avisa
        con un mensaje accionable en vez de un ImportError críptico.
        """
        try:
            from sshtunnel import SSHTunnelForwarder
        except ImportError:
            raise RuntimeError(
                "Para usar túnel SSH instalá el paquete: pip install sshtunnel")

        s = self.ssh
        destino_host = self.params["servidor"] or "127.0.0.1"
        destino_puerto = int(self.params["puerto"] or
                             MOTORES[self.motor].get("puerto_default") or 0)
        if not destino_puerto:
            raise RuntimeError("Indicá el puerto de la base para usar túnel SSH.")

        kwargs = dict(
            ssh_username=s.get("usuario"),
            remote_bind_address=(destino_host, destino_puerto),
        )
        if s.get("clave_privada"):
            kwargs["ssh_pkey"] = s["clave_privada"]
            if s.get("passphrase"):
                kwargs["ssh_private_key_password"] = s["passphrase"]
        else:
            kwargs["ssh_password"] = s.get("password")

        self._tunel = SSHTunnelForwarder(
            (s.get("host"), int(s.get("puerto") or 22)), **kwargs)
        self._tunel.start()
        # a partir de acá la base se ve en localhost:<puerto_local>
        self.params["servidor"] = "127.0.0.1"
        self.params["puerto"] = self._tunel.local_bind_port

    # ── conexión ──────────────────────────────────────────────
    def conectar(self):
        if self.ssh and self.motor != "sqlite":
            self._abrir_tunel()
        p = self.params
        if self.motor == "sqlite":
            # mode=ro: el propio SQLite rechaza cualquier escritura, sin
            # depender de que el SQL se haya validado antes. Se arma la URI
            # con pathname2url para que ande igual con rutas de Windows y
            # con espacios en el nombre.
            uri = f"file:{pathname2url(os.path.abspath(self.ruta))}?mode=ro"
            try:
                self._con = sqlite3.connect(uri, uri=True, check_same_thread=False)
            except sqlite3.OperationalError as e:
                # mode=ro no crea el archivo si no existe (a diferencia del
                # connect común, que devolvía una base vacía y dejaba al
                # usuario mirando "0 tablas" sin entender por qué).
                if not os.path.exists(self.ruta):
                    raise FileNotFoundError(
                        f"No se encontró la base de datos: {self.ruta}\n"
                        "Revisá la ruta. Si querés probar sin base propia, "
                        "generá la demo con: python generar_db_demo.py") from e
                raise
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
            # Read-only a nivel sesión, igual que ya se hacía en Postgres y
            # SQL Server. Es defensa en profundidad: la barrera principal es
            # asegurar_solo_lectura(). Si el servidor es viejo y no soporta
            # la sentencia, se sigue igual en vez de dejar al cliente sin
            # poder conectarse.
            try:
                with self._con.cursor() as _c:
                    _c.execute("SET SESSION TRANSACTION READ ONLY")
            except Exception:
                pass
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
        # el túnel se cierra siempre, aunque la conexión ya estuviera caída:
        # dejarlo abierto deja un puerto escuchando en la máquina del cliente
        if self._tunel is not None:
            try:
                self._tunel.stop()
            finally:
                self._tunel = None

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
    @property
    def marcador_param(self):
        """Marcador de parámetros del driver: '?' o '%s' según el motor."""
        return "%s" if self.motor in ("mysql", "postgres") else "?"

    def ejecutar(self, sql, limite=5000, params=None):
        """Ejecuta un SELECT y devuelve (columnas, filas, sql_ejecutado).

        `params` permite consultas parametrizadas (las variables de los
        cuadernos): el valor viaja aparte del SQL, así que su contenido
        nunca se interpreta como código.

        Lanza SQLNoPermitido si el SQL no es de solo lectura: la barrera
        está acá, en el punto de ejecución, y no solo en motor.py.
        """
        asegurar_solo_lectura(sql)
        sql = _aplicar_limite(sql, self.dialecto, limite)
        cur = self._con.cursor()
        if params:
            cur.execute(sql, tuple(params))
        else:
            cur.execute(sql)
        cols = [d[0] for d in cur.description]
        # fetchmany(limite+1) en vez de fetchall: red de seguridad si el tope
        # no se pudo inyectar en el SQL. _aplicar_limite no puede meter TOP en
        # una consulta que empieza con WITH (SQL Server) y el prompt pide CTEs,
        # así que sin esto una consulta con CTE traía la tabla entera a memoria.
        filas = [tuple(r) for r in cur.fetchmany(limite)]
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
