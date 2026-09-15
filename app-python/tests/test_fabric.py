# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_fabric.py — conectar a Microsoft Fabric
==================================================================
Fabric no es un motor nuevo: es SQL Server con otra puerta de entrada.
Habla TDS en el 1433, dialecto T-SQL, catálogo por sys.*. Lo único
distinto es que NO acepta usuario y contraseña de SQL — solo Entra ID.

Por eso lo que se prueba acá es exactamente eso: la cadena de conexión
(que decide la postura de seguridad) y la tolerancia del catálogo a lo
que Fabric no tiene. Todo lo demás ya está probado para SQL Server y no
cambia.

Lo que NO se puede probar sin un tenant de Azure delante: que la
conexión efectivamente abra. Eso se confirma recién contra Fabric de
verdad. Lo que sí se prueba es todo lo que decide ANTES de abrirla, que
es donde se cometen los errores caros.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import conectores  # noqa: E402
from catalogo import extraer_catalogo_mssql  # noqa: E402

_pasadas = _falladas = 0


def test(nombre):
    def deco(fn):
        global _pasadas, _falladas
        try:
            fn()
            print(f"  ✓ {nombre}")
            _pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}")
            _falladas += 1
    return deco


def campos(cadena):
    """La cadena ODBC como dict, para afirmar sobre claves y no por substring."""
    d = {}
    for parte in cadena.split(";"):
        if "=" in parte:
            k, _, v = parte.partition("=")
            d[k.strip()] = v.strip()
    return d


SERVIDOR = "abc123.datawarehouse.fabric.microsoft.com"


print("\n== La cadena de conexión: seguridad ==")


@test("SIEMPRE cifra, en los tres modos")
def _():
    for modo in conectores.AUTH_FABRIC:
        extra = dict(usuario="app-id", password="secreto") if modo == "spn" else {}
        c = campos(conectores.cadena_fabric(SERVIDOR, "Lakehouse", auth=modo, **extra))
        assert c.get("Encrypt") == "yes", f"{modo}: sin Encrypt=yes"


@test("NUNCA acepta cualquier certificado (la diferencia con el SQL Server de acá al lado)")
def _():
    # En el SQL Server interno se usa TrustServerCertificate=yes porque esos
    # servidores tienen certificados autofirmados. Fabric tiene uno público
    # de verdad: aceptarle cualquiera solo habilita a un intermediario a
    # hacerse pasar por Microsoft y leer las consultas del cliente.
    for modo in conectores.AUTH_FABRIC:
        extra = dict(usuario="app-id", password="secreto") if modo == "spn" else {}
        c = campos(conectores.cadena_fabric(SERVIDOR, "Lakehouse", auth=modo, **extra))
        assert "TrustServerCertificate" not in c, (
            f"{modo}: la cadena confía en cualquier certificado")


@test("pide el ODBC Driver 18 (el 17 no soporta ActiveDirectoryDefault)")
def _():
    c = campos(conectores.cadena_fabric(SERVIDOR, "Lakehouse"))
    assert "18" in c["DRIVER"], c["DRIVER"]


print("\n== Los tres modos de autenticación ==")


@test("interactivo: abre el navegador y no guarda ningún secreto")
def _():
    c = campos(conectores.cadena_fabric(SERVIDOR, "Lakehouse", auth="interactivo"))
    assert c["Authentication"] == "ActiveDirectoryInteractive", c
    assert "PWD" not in c, "el modo interactivo no debería llevar contraseña"
    assert "UID" not in c, "sin mail, no se manda UID vacío"


@test("interactivo con mail: lo precarga en la pantalla de Microsoft")
def _():
    c = campos(conectores.cadena_fabric(SERVIDOR, "Lakehouse",
                                        auth="interactivo", usuario="m@adium.com"))
    assert c["UID"] == "m@adium.com", c
    assert "PWD" not in c


@test("service principal: Application ID + secreto, para lo desatendido")
def _():
    c = campos(conectores.cadena_fabric(SERVIDOR, "Warehouse", auth="spn",
                                        usuario="1111-2222", password="s3cr3t"))
    assert c["Authentication"] == "ActiveDirectoryServicePrincipal", c
    assert c["UID"] == "1111-2222" and c["PWD"] == "s3cr3t", c


@test("service principal SIN credenciales corta con un mensaje que dice qué poner")
def _():
    try:
        conectores.cadena_fabric(SERVIDOR, "Warehouse", auth="spn")
    except ValueError as e:
        assert "client) ID" in str(e), f"el mensaje no dice qué es el usuario: {e}"
        return
    raise AssertionError("no cortó: armó una cadena de SPN sin credenciales")


@test("automatico: ni usuario ni contraseña (notebook de Fabric, az login, managed identity)")
def _():
    c = campos(conectores.cadena_fabric(SERVIDOR, "Lakehouse", auth="automatico"))
    assert c["Authentication"] == "ActiveDirectoryDefault", c
    assert "UID" not in c and "PWD" not in c, c


@test("un modo inventado no arma una cadena silenciosamente rota")
def _():
    try:
        conectores.cadena_fabric(SERVIDOR, "Lakehouse", auth="sql")
    except ValueError as e:
        assert "interactivo" in str(e), "el error no lista los modos válidos"
        return
    raise AssertionError("aceptó un modo de autenticación que no existe")


@test("el navegador de la autenticación interactiva tiene más tiempo que el resto")
def _():
    # Con los 30 segundos de siempre, loguearse con MFA llega tarde y el
    # error dice "timeout", que manda a mirar la red en vez de la pantalla
    # de Microsoft que quedó abierta esperando.
    inter = int(campos(conectores.cadena_fabric(SERVIDOR, "L", auth="interactivo"))
                ["Connection Timeout"])
    auto = int(campos(conectores.cadena_fabric(SERVIDOR, "L", auth="automatico"))
               ["Connection Timeout"])
    assert inter > auto, f"interactivo {inter}s no es mayor que automático {auto}s"


@test("sin servidor, el error dice DÓNDE copiarlo del portal")
def _():
    try:
        conectores.cadena_fabric("", "Lakehouse")
    except ValueError as e:
        assert "SQL analytics endpoint" in str(e), f"mensaje poco accionable: {e}"
        return
    raise AssertionError("armó una cadena sin servidor")


print("\n== Se integra sin tocar el resto del motor ==")


@test("comparte el dialecto T-SQL, así el tope de filas usa TOP y no LIMIT")
def _():
    assert conectores.MOTORES["fabric"]["dialecto"] == \
        conectores.MOTORES["sqlserver"]["dialecto"]
    con_tope = conectores._aplicar_limite(
        "SELECT nombre FROM clientes", conectores.MOTORES["fabric"]["dialecto"], 100)
    assert "TOP 100" in con_tope, con_tope
    assert "LIMIT" not in con_tope, f"le puso LIMIT a T-SQL: {con_tope}"


@test("la barrera de solo lectura rige igual (Fabric Warehouse SÍ es escribible)")
def _():
    # El endpoint de un Lakehouse es de solo lectura por diseño, pero un
    # Warehouse de Fabric acepta escrituras. O sea que acá la barrera del
    # producto no es redundante: es la única que queda.
    for sql in ("DELETE FROM ventas", "UPDATE ventas SET x=1",
                "DROP TABLE ventas", "SELECT * INTO copia FROM ventas"):
        try:
            conectores.asegurar_solo_lectura(sql)
        except conectores.SQLNoPermitido:
            continue
        raise AssertionError(f"dejó pasar: {sql}")


print("\n== El catálogo aguanta lo que Fabric no tiene ==")


class CursorFalso:
    """Cursor que responde como el SQL endpoint de un Lakehouse.

    Devuelve columnas (sys.columns existe y está poblado) pero falla en
    sys.partitions y en las claves foráneas, que es exactamente lo que
    pasa contra Fabric: las tablas son archivos Delta, no hay particiones
    con filas contadas ni FKs declaradas.
    """

    def __init__(self, falla_en=("sys.partitions", "sys.foreign_keys")):
        self.falla_en = falla_en
        self._filas = []

    def execute(self, sql, *a):
        if any(f in sql for f in self.falla_en):
            raise RuntimeError("Invalid object name (simulado: Fabric)")
        if "sys.columns" in sql and "sys.types" in sql:
            self._filas = [("ventas", "id_venta", "bigint", 0, 0),
                           ("ventas", "id_cliente", "bigint", 1, 0),
                           ("clientes", "id_cliente", "bigint", 0, 0),
                           ("clientes", "nombre", "varchar", 1, 0)]
        elif "sys.partitions" in sql:
            self._filas = [("ventas", 1000), ("clientes", 50)]
        elif "sys.foreign_keys" in sql:
            self._filas = [("ventas", "id_cliente", "clientes", "id_cliente")]
        else:
            self._filas = []
        return self

    def fetchall(self):
        return self._filas


class ConFalso:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur


@test("SIN sys.partitions ni FKs, el catálogo sale igual con sus columnas")
def _():
    cat = extraer_catalogo_mssql(ConFalso(CursorFalso()))
    assert set(cat["tablas"]) == {"ventas", "clientes"}, cat["tablas"].keys()
    assert len(cat["tablas"]["ventas"]["columnas"]) == 2


@test("el tamaño queda en None, NO en 0 (no saber no es estar vacía)")
def _():
    # Reportar 0 filas sería peor que no reportar nada: la ficha del RAG le
    # diría a la IA que la tabla está vacía y el panel de frescura pintaría
    # una tabla llena como si no tuviera datos.
    cat = extraer_catalogo_mssql(ConFalso(CursorFalso()))
    assert cat["tablas"]["ventas"]["n_filas"] is None, cat["tablas"]["ventas"]


@test("sin FKs declaradas, los joins se infieren por nombre de columna")
def _():
    cat = extraer_catalogo_mssql(ConFalso(CursorFalso()))
    assert cat["fks"] == [], cat["fks"]
    assert "id_cliente" in cat["joins_inferidos"], cat["joins_inferidos"]
    assert set(cat["joins_inferidos"]["id_cliente"]) == {"ventas", "clientes"}


@test("contra un SQL Server de verdad NO se perdió nada (sin regresión)")
def _():
    # El mismo extractor, con un cursor que sí responde las tres consultas:
    # tiene que seguir trayendo tamaños y FKs como siempre.
    cat = extraer_catalogo_mssql(ConFalso(CursorFalso(falla_en=())))
    assert cat["tablas"]["ventas"]["n_filas"] == 1000, cat["tablas"]["ventas"]
    assert cat["fks"] == [{"tabla_origen": "ventas", "columna_origen": "id_cliente",
                           "tabla_destino": "clientes",
                           "columna_destino": "id_cliente"}], cat["fks"]


print(f"\n  {_pasadas} pasadas · {_falladas} falladas\n")
sys.exit(1 if _falladas else 0)
