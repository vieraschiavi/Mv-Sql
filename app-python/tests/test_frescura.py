# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_frescura.py — el panel de frescura de datos
==================================================================
Lo que este panel promete es fuerte: "estos datos están al día". Si se
equivoca, un informe con datos viejos pasa por bueno — que es peor que no
tener el panel, porque agrega confianza donde no la había.

Lo que se cubre, en orden de lo que más duele si falla:

  1. Que ELIJA BIEN LA COLUMNA. `fecha_carga` y `fecha_nacimiento` son las
     dos DATE; solo una dice cuándo entró el dato. Elegir mal no da error:
     da un panel que informa con seguridad la fecha equivocada.
  2. Que el SQL sea SOLO LECTURA y con los identificadores citados según
     el motor.
  3. Que una tabla que falla no se lleve puesto el panel entero.
  4. Que una fecha futura no se pinte de verde.
"""
import os
import sys
from datetime import datetime, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import frescura  # noqa: E402

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


def col(nombre, tipo):
    return {"columna": nombre, "tipo": tipo, "nullable": True, "pk": False}


AHORA = datetime(2026, 9, 5, 12, 0, 0)


print("\n== Detección de la columna de fecha ==")


@test("reconoce los tipos de fecha de los cuatro motores")
def _():
    for tipo in ("DATE", "datetime", "DATETIME2(7)", "smalldatetime",
                 "timestamp without time zone", "TIMESTAMPTZ", "datetimeoffset"):
        assert frescura.es_columna_fecha(tipo), f"no reconoció {tipo}"


@test("NO toma como fecha lo que no lo es")
def _():
    for tipo in ("varchar(50)", "int", "decimal(18,2)", "bit", "text", "uuid"):
        assert not frescura.es_columna_fecha(tipo), f"tomó {tipo} como fecha"


@test("descarta 'time': una hora sin día no dice de cuándo es el dato")
def _():
    assert not frescura.es_columna_fecha("time")


@test("ELIGE fecha_carga POR SOBRE fecha_nacimiento (las dos son DATE)")
def _():
    # El caso que motiva el módulo entero: elegir mal no da error, da un
    # panel que informa con seguridad la fecha equivocada.
    info = {"columnas": [col("id", "int"), col("fecha_nacimiento", "date"),
                         col("fecha_carga", "datetime")]}
    columna, seguro = frescura.elegir_columna(info)
    assert columna == "fecha_carga", f"eligió {columna}"
    assert seguro is True


@test("prefiere la fecha de CARGA sobre la de creación del registro")
def _():
    info = {"columnas": [col("created_at", "datetime"), col("load_date", "datetime")]}
    assert frescura.elegir_columna(info)[0] == "load_date"


@test("con nombres en inglés funciona igual")
def _():
    info = {"columnas": [col("customer_birth_date", "date"), col("etl_updated", "timestamp")]}
    assert frescura.elegir_columna(info)[0] == "etl_updated"


@test("SIN NOMBRE RECONOCIBLE usa la fecha que hay, pero AVISA que es aproximada")
def _():
    # Es mejor un dato con reserva que ninguno — siempre que la reserva se
    # vea. Si `seguro` volviera True acá, la pantalla afirmaría algo que no
    # puede afirmar.
    info = {"columnas": [col("id", "int"), col("vencimiento", "date")]}
    columna, seguro = frescura.elegir_columna(info)
    assert columna == "vencimiento"
    assert seguro is False, "no puede darla por confiable: el nombre no habla de cargas"


@test("UNA FECHA DE NACIMIENTO NO SE DA POR CONFIABLE (caso real de la base demo)")
def _():
    # Encontrado corriendo el panel contra cartera_demo.db: la tabla
    # `clientes` solo tiene `fecha_nacimiento`, y como contiene "fecha"
    # calificaba como marca de carga. El panel informaba con total
    # seguridad "atrasada hace 8653 días". Se usa igual —es lo único que
    # hay— pero marcada como aproximada.
    info = {"columnas": [col("id", "int"), col("fecha_nacimiento", "date")]}
    columna, seguro = frescura.elegir_columna(info)
    assert columna == "fecha_nacimiento"
    assert seguro is False, "una fecha de nacimiento no puede darse por fecha de carga"


@test("tampoco un vencimiento ni una fecha genérica")
def _():
    for nombre in ("fecha_vencimiento", "fecha_otorgado", "date_value", "hora_corte"):
        info = {"columnas": [col(nombre, "datetime")]}
        assert frescura.elegir_columna(info)[1] is False, f"{nombre} se dio por confiable"


@test("pero una fecha de alta o de creación SÍ es una marca de carga válida")
def _():
    for nombre in ("fecha_alta", "created_at", "fecha_carga", "etl_ts", "load_dt"):
        info = {"columnas": [col(nombre, "datetime")]}
        assert frescura.elegir_columna(info)[1] is True, f"{nombre} quedó como aproximada"


@test("una tabla sin ninguna columna de fecha se reporta como tal")
def _():
    info = {"columnas": [col("id", "int"), col("nombre", "varchar(50)")]}
    assert frescura.elegir_columna(info) == (None, False)


@test("ante empate gana la primera declarada, no una cualquiera")
def _():
    info = {"columnas": [col("fecha_a", "date"), col("fecha_b", "date")]}
    assert frescura.elegir_columna(info)[0] == "fecha_a"


print("\n== El SQL que genera ==")


@test("ES SOLO LECTURA: pasa la misma barrera que el resto del producto")
def _():
    import conectores
    sql = frescura.sql_frescura("ventas", "fecha_carga", "PostgreSQL")
    conectores.asegurar_solo_lectura(sql)      # lanza si no es SELECT/WITH


@test("cita los identificadores según el motor")
def _():
    assert frescura.sql_frescura("ventas", "f", "SQL Server (T-SQL)") == \
        "SELECT MAX([f]) AS ultima_carga FROM [ventas]"
    assert frescura.sql_frescura("ventas", "f", "MySQL") == \
        "SELECT MAX(`f`) AS ultima_carga FROM `ventas`"
    assert frescura.sql_frescura("ventas", "f", "PostgreSQL") == \
        'SELECT MAX("f") AS ultima_carga FROM "ventas"'


@test("cita esquema.tabla parte por parte, no como un solo nombre")
def _():
    assert frescura.sql_frescura("dbo.ventas", "f", "SQL Server (T-SQL)") == \
        "SELECT MAX([f]) AS ultima_carga FROM [dbo].[ventas]"


@test("UN NOMBRE CON SQL ADENTRO NO SE INTERPOLA: lanza")
def _():
    # Los nombres vienen del catálogo, pero la barrera no puede depender de
    # que el origen sea confiable: deja de serlo el día que alguien le
    # cambia el origen.
    for malo in ("ventas; DROP TABLE clientes", "ventas--", "ven tas", "1=1"):
        try:
            frescura.sql_frescura(malo, "f", "PostgreSQL")
            raise AssertionError(f"aceptó un identificador peligroso: {malo!r}")
        except ValueError:
            pass


print("\n== Estado: al día, atrasada, sin fecha ==")


@test("cargada hace 3 horas con frecuencia diaria: al día")
def _():
    e, h = frescura.estado(AHORA - timedelta(hours=3), AHORA, "diaria")
    assert e == "al_dia", e
    assert 2.9 < h < 3.1


@test("un proceso diario de la madrugada mirado a la mañana SIGUE al día")
def _():
    # 30 horas: corrió a las 3 AM de ayer y se mira hoy a las 9. Sin el
    # margen sobre las 24 h exactas, todo proceso nocturno aparecería en
    # rojo todas las mañanas y el panel se volvería ruido que se ignora.
    e, _ = frescura.estado(AHORA - timedelta(hours=30), AHORA, "diaria")
    assert e == "al_dia", f"marcó atrasada una carga normal de la madrugada ({e})"


@test("ATRASADA de verdad: cinco días sin cargar con frecuencia diaria")
def _():
    e, _ = frescura.estado(AHORA - timedelta(days=5), AHORA, "diaria")
    assert e == "atrasada", e


@test("la misma antigüedad con frecuencia semanal está al día")
def _():
    e, _ = frescura.estado(AHORA - timedelta(days=5), AHORA, "semanal")
    assert e == "al_dia", e


@test("sin fecha (tabla vacía o columna toda en NULL) no se inventa nada")
def _():
    assert frescura.estado(None, AHORA)[0] == "sin_fecha"


@test("UNA FECHA FUTURA NO SE PINTA DE VERDE")
def _():
    # Reloj mal puesto o carga con fecha proyectada. Darla por "al día"
    # esconde justo el problema que hay que ver.
    e, _ = frescura.estado(AHORA + timedelta(days=2), AHORA, "diaria")
    assert e == "futura", e


@test("acepta lo que devuelva cada driver: str, date y datetime")
def _():
    from datetime import date
    for valor in ("2026-09-05 09:00:00", "2026-09-05", date(2026, 9, 5),
                  datetime(2026, 9, 5, 9, 0)):
        e, _ = frescura.estado(valor, AHORA, "diaria")
        assert e == "al_dia", f"{valor!r} dio {e}"


@test("una fecha con zona horaria no revienta la resta")
def _():
    e, _ = frescura.estado("2026-09-05T09:00:00+00:00", AHORA, "diaria")
    assert e == "al_dia", e


print("\n== analizar(): el panel completo ==")

CATALOGO = {"tablas": {
    "ventas":   {"columnas": [col("id", "int"), col("fecha_carga", "datetime")], "n_filas": 1000},
    "clientes": {"columnas": [col("id", "int"), col("alta", "date")], "n_filas": 50},
    "config":   {"columnas": [col("clave", "varchar(20)")], "n_filas": 5},
}}


def ejecutor(respuestas):
    def correr(sql):
        for tabla, valor in respuestas.items():
            if tabla in sql:
                if isinstance(valor, Exception):
                    raise valor
                return (["ultima_carga"], [[valor]], sql)
        return (["ultima_carga"], [[None]], sql)
    return correr


@test("informa cada tabla con su estado")
def _():
    filas = frescura.analizar(None, CATALOGO, AHORA, "diaria", ejecutar=ejecutor({
        "ventas": AHORA - timedelta(hours=2),
        "clientes": AHORA - timedelta(days=9),
    }))
    por_tabla = {f["tabla"]: f for f in filas}
    assert por_tabla["ventas"]["estado"] == "al_dia"
    assert por_tabla["clientes"]["estado"] == "atrasada"
    assert por_tabla["config"]["estado"] == "sin_fecha"


@test("la cantidad de filas sale del CATÁLOGO, sin un COUNT(*) por tabla")
def _():
    # Un COUNT(*) por cada objeto del esquema es el costo que convertiría
    # este panel en algo que nadie abre dos veces.
    sqls = []
    def espia(sql):
        sqls.append(sql)
        return (["ultima_carga"], [[AHORA]], sql)
    filas = frescura.analizar(None, CATALOGO, AHORA, ejecutar=espia)
    assert all("count" not in s.lower() for s in sqls), f"hay COUNT: {sqls}"
    assert {f["tabla"]: f["n_filas"] for f in filas}["ventas"] == 1000


@test("UNA TABLA QUE FALLA NO SE LLEVA PUESTO EL PANEL")
def _():
    # Permisos, tabla renombrada, tipo raro. Que se caiga entero por una de
    # cuarenta es lo contrario de monitorear.
    filas = frescura.analizar(None, CATALOGO, AHORA, ejecutar=ejecutor({
        "ventas": PermissionError("sin permisos sobre ventas"),
        "clientes": AHORA,
    }))
    por_tabla = {f["tabla"]: f for f in filas}
    assert por_tabla["ventas"]["estado"] == "error"
    assert "permisos" in por_tabla["ventas"]["error"]
    assert por_tabla["clientes"]["estado"] == "al_dia", "las demás tienen que informarse igual"


@test("PRIMERO LO QUE NECESITA ATENCIÓN: las atrasadas arriba")
def _():
    filas = frescura.analizar(None, CATALOGO, AHORA, "diaria", ejecutar=ejecutor({
        "ventas": AHORA,
        "clientes": AHORA - timedelta(days=9),
    }))
    assert filas[0]["tabla"] == "clientes", \
        f"la atrasada tiene que ir primero, quedó {[f['tabla'] for f in filas]}"


@test("se puede acotar a las tablas que el rol puede ver")
def _():
    # El producto recorta el catálogo por rol (equipo.py). El panel no
    # puede ser la puerta de atrás que revele que existe 'clientes'.
    filas = frescura.analizar(None, CATALOGO, AHORA, tablas={"ventas"},
                              ejecutar=ejecutor({"ventas": AHORA}))
    assert [f["tabla"] for f in filas] == ["ventas"]


@test("el resumen cuenta por estado")
def _():
    filas = frescura.analizar(None, CATALOGO, AHORA, "diaria", ejecutar=ejecutor({
        "ventas": AHORA,
        "clientes": AHORA - timedelta(days=9),
    }))
    r = frescura.resumen(filas)
    assert r == {"total": 3, "al_dia": 1, "atrasada": 1, "sin_fecha": 1,
                 "error": 0, "futura": 0}, r


@test("la antigüedad se lee de un vistazo")
def _():
    assert frescura.antiguedad_legible(None) == "—"
    assert frescura.antiguedad_legible(3) == "3 h"
    assert frescura.antiguedad_legible(52) == "2 d 4 h"
    assert frescura.antiguedad_legible(48) == "2 d", "con días de por medio, '0 h' es ruido"
    assert frescura.antiguedad_legible(0.5) == "< 1 h"


print(f"\n  {_pasadas} pasadas · {_falladas} falladas\n")
sys.exit(1 if _falladas else 0)
