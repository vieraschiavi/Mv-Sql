# © 2026 Martín Viera. Todos los derechos reservados.

"""Mapa semántico, RAG, validador y confianza, pieza por pieza. Correr: python3 tests/test_mapa_semantico.py

El banco (test_banco_esquemas.py) mide el camino entero sobre cuatro
esquemas. Acá va cada regla por separado, con el caso que la motivó, para
que cuando algo se rompa se sepa QUÉ se rompió.

Corre con la biblioteca estándar sola, como el resto de la suite.
"""
import os
import sqlite3
import sys
import tempfile
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

try:
    import requests  # noqa: F401
except ImportError:
    sys.modules.setdefault("requests", types.ModuleType("requests"))

import catalogo                  # noqa: E402
import equipo                    # noqa: E402
import mapa_semantico as MS      # noqa: E402
import motor                     # noqa: E402

pasadas = falladas = 0


def test(nombre):
    def deco(fn):
        global pasadas, falladas
        try:
            fn()
            print(f"  ✓ {nombre}")
            pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}")
            falladas += 1
    return deco


def col(nombre, tipo="TEXT", pk=False):
    return {"columna": nombre, "tipo": tipo, "pk": pk, "nullable": True}


def cat(tablas, fks=()):
    return {"tablas": {t: {"columnas": cs, "n_filas": 1, "muestras": {}} for t, cs in tablas.items()},
            "fks": list(fks), "joins_inferidos": {}}


def rel(mapa, origen, columna):
    """La relación deducida que sale de origen.columna, como (destino, columna_destino)."""
    for r in mapa["relaciones"]:
        if r["tabla_origen"] == origen and r["columna_origen"] == columna:
            return r["tabla_destino"], r["columna_destino"]
    return None


print("\n== Palabras ==")


@test("separa snake_case, camelCase, PascalCase, siglas y dígitos; saca tildes")
def _():
    assert MS.partir("FactSalesAmount") == ["fact", "sales", "amount"]
    assert MS.partir("cod_cliente") == ["cod", "cliente"]
    assert MS.partir("CustomerID") == ["customer", "id"]
    assert MS.partir("IDCliente") == ["id", "cliente"]
    assert MS.partir("Ventas2024") == ["ventas", "2024"]
    assert MS.partir("Región Año") == ["region", "ano"]


@test("singular consistente entre pregunta y esquema (ES/EN/PT)")
def _():
    for a, b in (("clientes", "cliente"), ("customers", "customer"), ("ciudades", "ciudad"),
                 ("cidades", "cidade"), ("categories", "category"), ("paises", "pais"), ("dates", "date")):
        assert MS.raiz(a) == MS.raiz(b), (a, b, MS.raiz(a), MS.raiz(b))


@test("ventas / sales / vendas caen en el mismo concepto; un año suma §fecha")
def _():
    for palabra in ("ventas", "sales", "vendas", "vendido", "revenue"):
        assert "§venta" in MS.analizar(palabra), palabra
    assert "§cliente" in MS.analizar("customers") and "§cliente" in MS.analizar("clientes")
    assert "§fecha" in MS.analizar("en 2024")


@test("la plantilla fija de la ficha («TABLA:», «Cantidad de filas», tipos, NOT NULL) no se indexa")
def _():
    bolsa = MS.bolsa_de_ficha({"tabla": "x", "texto": "TABLA: x\nCantidad de filas: 1,000\nColumnas:\n"
                                                     "  - nombre (VARCHAR(20)) NOT NULL [PK]"})
    assert "§cantidad" not in bolsa and "varchar" not in bolsa and "tabla" not in bolsa, bolsa
    assert "nombr" in bolsa, bolsa


print("\n== Relaciones deducidas por el nombre ==")


@test("cliente_id → clientes.id (la PK de la tabla destino)")
def _():
    m = MS.construir_mapa(cat({"clientes": [col("id", "INTEGER", True), col("nombre")],
                               "facturas": [col("nro", "INTEGER", True), col("cliente_id", "INTEGER")]}))
    assert rel(m, "facturas", "cliente_id") == ("clientes", "id"), m["relaciones"]


@test("id_cliente, IdCliente, ClienteKey, cod_cliente, cliente_cod → clientes")
def _():
    for columna in ("id_cliente", "IdCliente", "ClienteKey", "cod_cliente", "cliente_cod", "codigo_cliente"):
        m = MS.construir_mapa(cat({"clientes": [col("cod", "TEXT", True), col("nombre")],
                                   "ventas": [col(columna), col("importe", "REAL")]}))
        assert rel(m, "ventas", columna) == ("clientes", "cod"), (columna, m["relaciones"])


@test("CustomerID → Customers (plural, inglés) y DateKey → DimDate (prefijo dim)")
def _():
    m = MS.construir_mapa(cat({"Customers": [col("CustomerID", "TEXT", True)],
                               "Orders": [col("OrderID", "INTEGER", True), col("CustomerID")],
                               "DimDate": [col("DateKey", "INTEGER")],
                               "FactSales": [col("DateKey", "INTEGER"), col("Amount", "REAL")]}))
    assert rel(m, "Orders", "CustomerID") == ("Customers", "CustomerID")
    assert rel(m, "FactSales", "DateKey") == ("DimDate", "DateKey"), m["relaciones"]


@test("nro_pedido → la tabla `order` (pedido = order, por concepto) aunque no se llame igual")
def _():
    m = MS.construir_mapa(cat({"order": [col("nro_pedido", "INTEGER", True)],
                               "pedido_items": [col("nro_pedido", "INTEGER", True), col("renglon", "INTEGER", True)]}))
    assert rel(m, "pedido_items", "nro_pedido") == ("order", "nro_pedido"), m["relaciones"]


@test("customer_code → customers; num_factura → facturas")
def _():
    m = MS.construir_mapa(cat({"customers": [col("code", "TEXT", True)],
                               "facturas": [col("num_factura", "INTEGER", True)],
                               "cobros": [col("customer_code"), col("num_factura", "INTEGER")]}))
    assert rel(m, "cobros", "customer_code") == ("customers", "code")
    assert rel(m, "cobros", "num_factura") == ("facturas", "num_factura")


@test("misma columna que es la PK de otra tabla (CUIT) → relación")
def _():
    m = MS.construir_mapa(cat({"contribuyentes": [col("cuit", "TEXT", True)],
                               "facturas": [col("cuit"), col("importe", "REAL")]}))
    assert rel(m, "facturas", "cuit") == ("contribuyentes", "cuit")


@test("NO inventa: `id` genérico en varias tablas, dos hechos que comparten una clave sin maestro")
def _():
    m = MS.construir_mapa(cat({"a": [col("id", "INTEGER", True)], "b": [col("id", "INTEGER", True)],
                               "ventas": [col("cod_cliente"), col("importe", "REAL")],
                               "cobros": [col("cod_cliente"), col("monto", "REAL")]}))
    assert m["relaciones"] == [], m["relaciones"]


@test("las FKs declaradas se respetan (y SQLite «REFERENCES t» sin columna va a su PK)")
def _():
    m = MS.construir_mapa(cat({"t": [col("x", "INTEGER", True)], "u": [col("t_ref", "INTEGER")]},
                              [{"tabla_origen": "u", "columna_origen": "t_ref", "tabla_destino": "t",
                                "columna_destino": None}]))
    assert m["relaciones"][0]["origen"] == "declarada" and rel(m, "u", "t_ref") == ("t", "x")


print("\n== Roles y caminos ==")


@test("roles de columna: clave, fecha, medida, atributo, bandera")
def _():
    roles = {c: MS.rol_columna(col(c, t, pk)) for c, t, pk in (
        ("cliente_id", "INTEGER", False), ("fecha_alta", "TEXT", False), ("Year", "INTEGER", False),
        ("importe", "DECIMAL(12,2)", False), ("ciudad", "VARCHAR(40)", False), ("pagada", "INTEGER", False),
        ("plazo_meses", "INTEGER", False), ("id", "INTEGER", True))}
    assert roles == {"cliente_id": "clave", "fecha_alta": "fecha", "Year": "fecha", "importe": "medida",
                     "ciudad": "atributo", "pagada": "bandera", "plazo_meses": "medida", "id": "clave"}, roles


@test("camino de JOINs con forma de valle: sí estrella y cadena; no hecho → dimensión → otro hecho")
def _():
    padres = {"pagos": ["cuotas"], "cuotas": ["creditos"], "creditos": ["sucursales", "clientes"],
              "facturas": ["vendedores"], "ventas_mes": ["vendedores"]}
    assert MS.camino_tablas(padres, "pagos", "sucursales") == ["pagos", "cuotas", "creditos", "sucursales"]
    assert MS.camino_tablas(padres, "clientes", "sucursales") == ["clientes", "creditos", "sucursales"]
    assert MS.camino_tablas(padres, "facturas", "ventas_mes") is None


print("\n== El bloque del prompt ==")

CANARIO = "VALOR-REAL-7f3a"
CAT_PROMPT = {"tablas": {
    "FactVentas": {"columnas": [col("ClienteKey", "INTEGER"), col("Importe", "REAL")], "muestras": {}},
    "DimCliente": {"columnas": [col("ClienteKey", "INTEGER"), col("Nombre")], "muestras": {"Nombre": [CANARIO]}},
    "nomina_sueldos": {"columnas": [col("ClienteKey", "INTEGER"), col("Sueldo", "REAL")], "muestras": {}},
    "Ventas Mensuales": {"columnas": [col("ClienteKey", "INTEGER"), col("Unidades", "INTEGER")], "muestras": {}},
}, "fks": [], "joins_inferidos": {}}


@test("lleva roles, sinónimos y los JOINs DEDUCIDOS de las tablas pedidas; cita lo que hay que citar")
def _():
    b = MS.bloque_prompt(MS.construir_mapa(CAT_PROMPT), ["FactVentas", "DimCliente", "Ventas Mensuales"])
    assert b.startswith("MAPA SEMÁNTICO"), b
    assert "FactVentas.ClienteKey = DimCliente.ClienteKey" in b, b
    assert '"Ventas Mensuales".ClienteKey = DimCliente.ClienteKey' in b, b
    assert "ventas | sales | vendas" in b and "medidas: Importe" in b, b
    assert "nomina_sueldos" not in b, "una tabla no pedida no aparece"


@test("nunca lleva valores de ejemplo, ni en modo normal ni en privado (el mapa no lee datos)")
def _():
    m = MS.construir_mapa(CAT_PROMPT)
    for privado in (False, True):
        assert CANARIO not in MS.bloque_prompt(m, list(CAT_PROMPT["tablas"]), privado=privado)


@test("privado: versión mínima (JOINs), sin roles ni sinónimos")
def _():
    b = MS.bloque_prompt(MS.construir_mapa(CAT_PROMPT), ["FactVentas", "DimCliente"], privado=True)
    assert "FactVentas.ClienteKey = DimCliente.ClienteKey" in b and "Tablas:" not in b, b


@test("recorte por rol: una tabla prohibida no aparece ni como relación ni como camino")
def _():
    visible = equipo.tablas_visibles(CAT_PROMPT, {"tablas": ["FactVentas", "DimCliente"]})
    m = MS.construir_mapa(visible)
    texto = MS.bloque_prompt(m) + repr(m)
    assert "nomina_sueldos" not in texto and "Ventas Mensuales" not in texto


print("\n== Catálogo SQLite ==")


@test("una tabla con espacio y otra llamada `order` no tumban la conexión; VARCHAR(n)/NVARCHAR/CHAR se muestrean")
def _():
    ruta = os.path.join(tempfile.mkdtemp(), "raro.db")
    con = sqlite3.connect(ruta)
    con.execute('CREATE TABLE "Ventas Mensuales" (periodo CHAR(7), zona NVARCHAR(20), nota VARCHAR(20), '
                "unidades INTEGER)")
    con.execute('CREATE TABLE "order" (nro INTEGER PRIMARY KEY, "estado actual" CLOB)')
    con.execute("INSERT INTO \"Ventas Mensuales\" VALUES ('2024-03', 'Norte', 'ok', 5)")
    con.execute("INSERT INTO \"order\" VALUES (1, 'P')")
    con.commit()
    con.close()
    c = catalogo.extraer_catalogo_sqlite(ruta)
    assert set(c["tablas"]) == {"Ventas Mensuales", "order"}
    assert c["tablas"]["Ventas Mensuales"]["n_filas"] == 1
    mues = c["tablas"]["Ventas Mensuales"]["muestras"]
    assert mues == {"periodo": ["2024-03"], "zona": ["Norte"], "nota": ["ok"]}, mues
    assert c["tablas"]["order"]["muestras"] == {"estado actual": ["P"]}


@test("las fichas traen índice y vecinas para el RAG, y los textos que viajan no cambian")
def _():
    m = MS.construir_mapa(CAT_PROMPT)
    f = {x["tabla"]: x for x in catalogo.catalogo_a_fichas(CAT_PROMPT)}["FactVentas"]
    assert "FactVentas" in f["indice"] and "ClienteKey" in f["indice"]
    assert set(f["vecinas"]) == set(m["vecinas"]["FactVentas"]) and "DimCliente" in f["padres"]
    assert f["texto"].startswith("TABLA: FactVentas") and CANARIO not in f["texto_min"]


print("\n== RAG ==")


@test("«sales by customer» y «ventas por cliente en 2024» encuentran la estrella (antes: similitud 0)")
def _():
    estrella = cat({"FactSales": [col("DateKey", "INTEGER"), col("CustomerKey", "INTEGER"),
                                  col("ProductKey", "INTEGER"), col("SalesAmount", "REAL")],
                    "DimCustomer": [col("CustomerKey", "INTEGER"), col("CustomerName")],
                    "DimProduct": [col("ProductKey", "INTEGER"), col("ProductName")],
                    "DimDate": [col("DateKey", "INTEGER"), col("Year", "INTEGER")],
                    "AuditLog": [col("EventTime"), col("UserName")],
                    "Config": [col("Clave"), col("Valor")]})
    r = motor.RecuperadorEsquema(catalogo.catalogo_a_fichas(estrella))
    for pregunta, necesarias in (("sales by customer", {"FactSales", "DimCustomer"}),
                                 ("ventas por cliente en 2024", {"FactSales", "DimCustomer", "DimDate"})):
        fichas, sims = r.recuperar(pregunta)
        assert len(fichas) == len(sims) and sims[0] > 0
        assert necesarias <= {f["tabla"] for f in fichas}, (pregunta, [f["tabla"] for f in fichas])


@test("suma las tablas puente del camino de JOINs (pagos … sucursales)")
def _():
    c = cat({"pagos": [col("pago_id", "INTEGER", True), col("cuota_id", "INTEGER"), col("importe_pagado", "REAL")],
             "cuotas": [col("cuota_id", "INTEGER", True), col("credito_id", "INTEGER")],
             "creditos": [col("credito_id", "INTEGER", True), col("sucursal_id", "INTEGER")],
             "sucursales": [col("sucursal_id", "INTEGER", True), col("nombre")],
             "usuarios": [col("login")], "parametros": [col("clave")], "auditoria": [col("evento")]})
    tablas = [f["tabla"] for f in motor.RecuperadorEsquema(catalogo.catalogo_a_fichas(c)).recuperar(
        "¿Cuánto se cobró por sucursal?", k=2)[0]]
    assert {"pagos", "cuotas", "creditos", "sucursales"} <= set(tablas), tablas


@test("fichas armadas a mano (sin índice) siguen funcionando, sin la plantilla fija")
def _():
    fichas = [{"tabla": "a", "texto": "TABLA: a\nCantidad de filas: 3\nColumnas:\n  - ventas (TEXT) NOT NULL"},
              {"tabla": "b", "texto": "TABLA: b\nCantidad de filas: 3\nColumnas:\n  - otra (TEXT)"}]
    fs, sims = motor.RecuperadorEsquema(fichas).recuperar("sales")
    assert fs[0]["tabla"] == "a" and sims[0] > 0 and sims[1] == 0


print("\n== Validador ==")

CAT_V = cat({"ventas": [col(c) for c in ("id", "fecha", "importe", "cliente_id", "last_update", "fecha_insert",
                                         "nombre")],
             "clientes": [col(c) for c in ("cliente_id", "nombre", "ciudad")],
             "Ventas Mensuales": [col("periodo"), col("importe")],
             "order": [col("nro", "INTEGER", True)]})


def limpio(sql):
    ok, problemas, adv = motor.validar_sql(sql, CAT_V)
    assert ok and not problemas and not adv, (sql, problemas, adv)


@test("palabras prohibidas sólo como palabra: last_update, fecha_insert, literales y comentarios pasan")
def _():
    limpio("SELECT r.last_update FROM ventas r")
    limpio("SELECT fecha_insert FROM ventas")
    limpio("SELECT nombre FROM ventas WHERE nombre <> 'insert into x' AND nombre <> 'drop shipping'")
    limpio("SELECT nombre FROM ventas -- drop table ventas")


@test("identificadores citados, esquema.tabla y palabras reservadas como nombre")
def _():
    limpio('SELECT "periodo", SUM(vm."importe") AS t FROM "Ventas Mensuales" vm GROUP BY "periodo"')
    limpio("SELECT [periodo] FROM [Ventas Mensuales]")
    limpio("SELECT `periodo` FROM `Ventas Mensuales`")
    limpio('SELECT o.nro FROM "order" o')
    limpio("SELECT v.importe FROM dbo.ventas v")        # antes: «Columna no reconocida: 'ventas'»
    limpio("SELECT dbo.ventas.importe FROM dbo.ventas")


@test("CTEs con lista de columnas y RECURSIVE; el FROM de EXTRACT/TRIM/SUBSTRING no es una tabla")
def _():
    limpio("WITH x(a, b) AS (SELECT cliente_id, importe FROM ventas) SELECT a, SUM(b) AS t FROM x GROUP BY a")
    limpio("WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 5) SELECT i FROM n")
    limpio("SELECT EXTRACT(YEAR FROM fecha) AS anio, SUM(importe) AS t FROM ventas GROUP BY EXTRACT(YEAR FROM fecha)")
    limpio("SELECT TRIM(BOTH ' ' FROM nombre) AS n FROM clientes")
    limpio("SELECT SUBSTRING(nombre FROM 2 FOR 3) AS s FROM clientes")


@test("dialectos: TOP, CAST, ::, INTERVAL, DATEADD, NOLOCK, ventanas, CASE, COLLATE")
def _():
    limpio("SELECT TOP 10 nombre FROM ventas ORDER BY importe DESC")
    limpio("SELECT CAST(importe AS DECIMAL(10,2)) AS x, CAST(fecha AS DATE) d FROM ventas")
    limpio("SELECT importe::numeric FROM ventas WHERE fecha >= CURRENT_DATE - INTERVAL '30 days'")
    limpio("SELECT DATEADD(month, -1, GETDATE()) AS f, DATEPART(year, fecha) AS y FROM ventas WITH (NOLOCK)")
    limpio("SELECT nombre, ROW_NUMBER() OVER (PARTITION BY nombre ORDER BY importe DESC) AS rn FROM ventas")
    limpio("SELECT CASE WHEN importe > 0 THEN 'a' ELSE 'b' END tipo FROM ventas")
    limpio("SELECT s.n FROM (SELECT nombre AS n FROM ventas) s")
    limpio("SELECT nombre COLLATE Latin1_General_CI_AI AS n FROM ventas")


@test("sigue rechazando DML/DDL, SELECT INTO, procedimientos y tablas inexistentes")
def _():
    for sql in ("DELETE FROM ventas", "WITH x AS (DELETE FROM ventas RETURNING *) SELECT * FROM x",
                "SELECT nombre INTO copia FROM ventas", "SELECT 1; DROP TABLE ventas",
                "UPDATE ventas SET importe = 0", "EXEC sp_executesql N'SELECT 1'", "SELECT xp_cmdshell('dir')",
                "SELECT * FROM ventas_2024"):
        ok, problemas, _adv = motor.validar_sql(sql, CAT_V)
        assert not ok and problemas, sql


@test("columna de OTRA tabla: advertencia precisa, con alias y sin alias")
def _():
    _ok, _p, adv = motor.validar_sql("SELECT v.ciudad FROM ventas v", CAT_V)
    assert adv == ["La columna 'ciudad' no existe en la tabla 'ventas' (alias 'v'); está en: clientes"], adv
    _ok, _p, adv = motor.validar_sql("SELECT ciudad FROM ventas", CAT_V)
    assert adv and "está en: clientes" in adv[0], adv
    _ok, _p, adv = motor.validar_sql("SELECT monto_total FROM ventas", CAT_V)
    assert adv == ["Columna no reconocida en el catálogo: 'monto_total'"], adv


@test("el parámetro ctes cuenta como tabla válida")
def _():
    assert not motor.validar_sql("SELECT a FROM paso_previo", CAT_V)[0]
    assert motor.validar_sql("SELECT a FROM paso_previo", CAT_V, ctes=["paso_previo"])[0]


print("\n== Confianza ==")


@test("compatibilidad: la firma vieja (posicional, sin joins_validos) sigue andando")
def _():
    c = motor.calcular_confianza(80, 0.2, True, 0, True, 1.0, "ok", 0)
    assert set(c) == {"puntaje", "margen", "intervalo", "componentes"}
    assert {"modelo", "rag", "validacion", "ejecucion"} <= set(c["componentes"])


@test("rechazado ≤ 30 aunque el modelo diga 99; usar CTE ya no suma")
def _():
    assert motor.calcular_confianza(99, 0.9, False, 0, False, cobertura=1.0)["puntaje"] <= 30
    con = motor.calcular_confianza(70, 0.2, True, 0, True, cobertura=1.0, ejecucion="ok")["puntaje"]
    sin = motor.calcular_confianza(70, 0.2, True, 0, False, cobertura=1.0, ejecucion="ok")["puntaje"]
    assert con == sin, (con, sin)


@test("válido + filas + JOINs del mapa + modelo 80 → ≥ 80; JOIN fuera del mapa → tope")
def _():
    bueno = motor.calcular_confianza(80, 0.0, True, 0, False, cobertura=0.0, ejecucion="ok", joins_validos=1.0)
    assert bueno["puntaje"] >= 80, bueno
    malo = motor.calcular_confianza(95, 0.5, True, 0, False, cobertura=1.0, ejecucion="ok", joins_validos=0.0)
    assert malo["puntaje"] <= 60 and malo["componentes"]["joins"] == 0, malo


@test("responder: un JOIN por columnas que no son relación baja la confianza y avisa")
def _():
    class Cx:
        dialecto = "SQLite"

        def ejecutar(self, sql, limite=5000, params=None):
            return ["x"], [(1,)], sql

    m = motor.MotorMVSQL.__new__(motor.MotorMVSQL)
    m.cx, m.catalogo = Cx(), cat({"clientes": [col("cliente_id", "INTEGER", True), col("nombre")],
                                  "ventas": [col("venta_id", "INTEGER", True), col("cliente_id", "INTEGER"),
                                             col("importe", "REAL")]})
    m.fichas = catalogo.catalogo_a_fichas(m.catalogo)
    m.recuperador = motor.RecuperadorEsquema(m.fichas)
    sistemas = []

    def con(sql):
        def completar(system, user, max_tokens=1500):
            sistemas.append(system)
            return f"SQL:\n{sql}\nCONFIANZA: 90\nSUPUESTOS: ninguno"
        return completar

    m._completar = con("SELECT c.nombre, SUM(v.importe) AS t FROM ventas v JOIN clientes c "
                       "ON c.cliente_id = v.cliente_id GROUP BY c.nombre")
    bien = m.responder("ventas por cliente", explicar=False)
    assert "ventas.cliente_id = clientes.cliente_id" in sistemas[0], "el JOIN deducido llega al prompt"
    m._completar = con("SELECT c.nombre, SUM(v.importe) AS t FROM ventas v JOIN clientes c "
                       "ON c.cliente_id = v.venta_id GROUP BY c.nombre")
    mal = m.responder("ventas por cliente", explicar=False)
    assert bien["joins_validos"] == 1.0 and mal["joins_validos"] == 0.0
    assert mal["confianza"]["puntaje"] < bien["confianza"]["puntaje"] and mal["confianza"]["puntaje"] <= 60
    assert any("JOIN fuera del mapa" in a for a in mal["advertencias"]), mal["advertencias"]


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
