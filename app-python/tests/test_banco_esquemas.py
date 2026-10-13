# © 2026 Martín Viera. Todos los derechos reservados.

"""Banco de verificación: ¿el motor se adapta a CUALQUIER esquema? Correr: python3 tests/test_banco_esquemas.py

El motor es 100 % LLM y acá no hay clave de IA. Lo que sí se puede medir sin
IA es todo lo determinístico que rodea al modelo, y es lo que decide si la
respuesta sale bien aunque el modelo sea bueno:

  (i)   RAG: ¿las tablas que necesita el SQL correcto llegan al prompt?
  (ii)  Validador: ¿el SQL correcto pasa sin rechazos falsos y ejecuta?
  (iii) Anti-alucinación: ¿un SQL inventado sale rechazado o con advertencia?
  (iv)  Mapa semántico: ¿cada JOIN del SQL correcto es una relación conocida
        (declarada o deducida)? ¿llega al prompt?
  (v)   Confianza: ¿el puntaje separa lo bueno de lo malo?

Cuatro esquemas que no se parecen entre sí, en SQLite (archivos temporales:
el extractor de catálogo abre su propia conexión y una base `:memory:` no se
comparte entre conexiones):

  a) cobranzas en español, snake_case, con FKs declaradas;
  b) estrella retail en inglés, PascalCase, SIN FKs ni PKs (como un lakehouse);
  c) ERP en español con claves cod_*/nro_*, una tabla «Ventas Mensuales» (con
     espacio) y otra llamada `order` (palabra reservada);
  d) estilo Northwind, inglés, tablas en plural y CustomerID.

Cada pregunta (ES/EN/PT) trae su SQL de oro y las tablas que usa. El «LLM» es
un oráculo que devuelve ese SQL con CONFIANZA 80: así se mide el camino
completo (RAG → prompt → validación → ejecución → confianza) sin inventar lo
que haría un modelo de verdad.

Corre con la biblioteca estándar sola (CI no instala requirements.txt) y está
escrito para poder correrse también contra el código anterior y comparar.
Todos los datos son sintéticos, con semilla fija.
"""
import inspect
import os
import random
import sqlite3
import sys
import tempfile
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

# El motor de antes importaba sklearn para el RAG; si no está, se stubea igual
# que en el resto de la suite (el motor de ahora no lo necesita).
try:
    import sklearn  # noqa: F401
except ImportError:
    for _n in ("sklearn", "sklearn.feature_extraction", "sklearn.feature_extraction.text",
               "sklearn.metrics", "sklearn.metrics.pairwise"):
        sys.modules.setdefault(_n, types.ModuleType(_n))
    sys.modules["sklearn.feature_extraction.text"].TfidfVectorizer = object
    sys.modules["sklearn.metrics.pairwise"].cosine_similarity = lambda *a, **k: None
try:
    import requests  # noqa: F401
except ImportError:
    sys.modules.setdefault("requests", types.ModuleType("requests"))

import catalogo            # noqa: E402
import control_resultado   # noqa: E402
import motor               # noqa: E402
from conectores import ConexionBD   # noqa: E402

try:
    import mapa_semantico as MS     # noqa: E402
except ImportError:                 # código anterior: no había mapa semántico
    MS = None

CONF_LLM_ORO = 80
_JOINS_EN_CONFIANZA = "joins_validos" in inspect.signature(motor.calcular_confianza).parameters

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


# ══════════════════════════════════════════════════════════════
# Esquemas
# ══════════════════════════════════════════════════════════════
def _fechas(rnd, anios=(2023, 2024)):
    a = rnd.choice(anios)
    return f"{a}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}"


def _datos_cobranzas(con, rnd):
    ciudades = ["Córdoba", "Rosario", "Mendoza", "La Plata", "Salta"]
    for i in range(1, 41):
        con.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?)",
                    (i, f"Cliente {i:03d}", f"DOC-{i:05d}", ciudades[i % 5], "Provincia " + "ABC"[i % 3],
                     rnd.choice(["Consumo", "Pyme", "Premium"]), _fechas(rnd, (2021, 2022)),
                     _fechas(rnd, (2023, 2024))))
    for i, nom in enumerate(["Centro", "Norte", "Sur", "Oeste"], 1):
        con.execute("INSERT INTO sucursales VALUES (?,?,?)", (i, f"Sucursal {nom}", ciudades[i]))
    cuota_id = pago_id = 0
    for cr in range(1, 81):
        plazo = rnd.choice([6, 12])
        monto = round(rnd.uniform(50_000, 500_000), 2)
        f_ot = _fechas(rnd)
        con.execute("INSERT INTO creditos VALUES (?,?,?,?,?,?,?,?)",
                    (cr, rnd.randint(1, 40), rnd.randint(1, 4), monto, round(rnd.uniform(40, 90), 1),
                     f_ot, plazo, rnd.choice(["vigente", "cancelado", "en mora"])))
        for n in range(1, plazo + 1):
            cuota_id += 1
            venc = f"{rnd.choice([2023, 2024, 2025])}-{rnd.randint(1, 12):02d}-10"
            pagada = rnd.random() < 0.6
            importe = round(monto / plazo, 2)
            con.execute("INSERT INTO cuotas VALUES (?,?,?,?,?,?)",
                        (cuota_id, cr, n, venc, importe, int(pagada)))
            if pagada:
                pago_id += 1
                con.execute("INSERT INTO pagos VALUES (?,?,?,?,?)",
                            (pago_id, cuota_id, _fechas(rnd), importe,
                             rnd.choice(["transferencia", "efectivo", "débito automático"])))
    for g in range(1, 151):
        con.execute("INSERT INTO gestiones_cobranza VALUES (?,?,?,?,?,?)",
                    (g, rnd.randint(1, 40), _fechas(rnd), rnd.choice(["teléfono", "email", "visita"]),
                     rnd.choice(["promesa de pago", "sin contacto", "rechazo"]), f"Gestor {rnd.randint(1, 6)}"))
    for u in range(1, 6):
        con.execute("INSERT INTO usuarios_sistema VALUES (?,?,?,?)",
                    (u, f"usuario{u}", rnd.choice(["admin", "consulta"]), _fechas(rnd)))
    con.execute("INSERT INTO parametros VALUES ('tasa_punitoria', '1.5', 'Tasa punitoria mensual')")


def _datos_retail(con, rnd):
    ciudades = [("Buenos Aires", "Argentina"), ("Santiago", "Chile"), ("Lima", "Peru"), ("Bogota", "Colombia")]
    for k in range(1, 31):
        ciu, pais = ciudades[k % 4]
        con.execute("INSERT INTO DimCustomer VALUES (?,?,?,?,?)",
                    (k, f"Customer {k:03d}", ciu, pais, rnd.choice(["Retail", "Wholesale", "Online"])))
    cats = {"Beverages": ["Soda", "Juice"], "Snacks": ["Chips", "Cookies"], "Dairy": ["Milk", "Cheese"]}
    pk = 0
    for cat, subs in cats.items():
        for sub in subs:
            for j in range(3):
                pk += 1
                con.execute("INSERT INTO DimProduct VALUES (?,?,?,?,?)",
                            (pk, f"{sub} {j + 1}", cat, sub, rnd.choice(["Acme", "Globex", "Initech"])))
    meses = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]
    claves = []
    for anio in (2023, 2024):
        for m in range(1, 13):
            for d in (5, 20):
                dk = anio * 10000 + m * 100 + d
                claves.append(dk)
                con.execute("INSERT INTO DimDate VALUES (?,?,?,?,?,?)",
                            (dk, f"{anio}-{m:02d}-{d:02d}", anio, m, meses[m - 1], f"Q{(m - 1) // 3 + 1}"))
    for s, (nom, reg) in enumerate([("Store North", "North"), ("Store South", "South"),
                                    ("Store East", "East"), ("Store West", "West")], 1):
        con.execute("INSERT INTO DimStore VALUES (?,?,?,?)", (s, nom, reg, ciudades[s % 4][0]))
    for sk in range(1, 401):
        q = rnd.randint(1, 20)
        precio = round(rnd.uniform(1, 30), 2)
        monto = round(q * precio, 2)
        con.execute("INSERT INTO FactSales VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (sk, rnd.choice(claves), rnd.randint(1, 30), rnd.randint(1, pk), rnd.randint(1, 4), q, precio,
                     monto, round(monto * rnd.uniform(0, 0.15), 2), round(monto * rnd.uniform(0.5, 0.8), 2)))
    for dk in claves[-4:]:
        for p in range(1, pk + 1):
            con.execute("INSERT INTO FactInventory VALUES (?,?,?,?)", (dk, p, rnd.randint(1, 4), rnd.randint(0, 200)))
    for i in range(1, 11):
        con.execute("INSERT INTO AuditLog VALUES (?,?,?,?)", (i, _fechas(rnd), f"user{i % 3}", "login"))


def _datos_erp(con, rnd):
    provincias = ["Buenos Aires", "Córdoba", "Santa Fe", "Mendoza"]
    for i in range(1, 31):
        con.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?)",
                    (f"C{i:04d}", f"Razón Social {i:03d} SA", f"30-{10000000 + i}-9", f"Localidad {i % 7}",
                     provincias[i % 4], rnd.choice(["RI", "MT", "CF"])))
    rubros = ["Ferretería", "Pinturas", "Drop Shipping", "Electricidad"]
    for i in range(1, 21):
        lista = round(rnd.uniform(100, 5000), 2)
        con.execute("INSERT INTO articulos VALUES (?,?,?,?,?)",
                    (f"A{i:04d}", f"Artículo {i:03d}", rubros[i % 4], lista, round(lista * rnd.uniform(0.4, 0.7), 2)))
    for i in range(1, 7):
        con.execute("INSERT INTO vendedores VALUES (?,?,?)", (f"V{i:02d}", f"Vendedor {i}", rnd.choice(["AMBA", "Interior"])))
    nro_fac = 0
    for p in range(1, 121):
        cli, ven = f"C{rnd.randint(1, 30):04d}", f"V{rnd.randint(1, 6):02d}"
        fecha = _fechas(rnd)
        con.execute('INSERT INTO "order" VALUES (?,?,?,?,?)', (p, cli, ven, fecha, rnd.choice(["P", "F", "A"])))
        neto = 0.0
        for r in range(1, rnd.randint(2, 4)):
            q, pu = rnd.randint(1, 10), round(rnd.uniform(100, 5000), 2)
            neto += q * pu
            con.execute("INSERT INTO pedido_items VALUES (?,?,?,?,?)", (p, r, f"A{rnd.randint(1, 20):04d}", q, pu))
        if rnd.random() < 0.8:
            nro_fac += 1
            con.execute("INSERT INTO facturas VALUES (?,?,?,?,?,?)",
                        (nro_fac, p, cli, fecha, round(neto, 2), round(neto * 0.21, 2)))
    for anio in (2023, 2024):
        for m in range(1, 13):
            for v in range(1, 7):
                for _ in range(2):
                    u = rnd.randint(1, 50)
                    con.execute('INSERT INTO "Ventas Mensuales" VALUES (?,?,?,?,?)',
                                (f"{anio}-{m:02d}", f"V{v:02d}", f"A{rnd.randint(1, 20):04d}", u,
                                 round(u * rnd.uniform(100, 5000), 2)))
    for i in range(1, 6):
        con.execute("INSERT INTO log_sincronizacion VALUES (?,?,?)", (i, _fechas(rnd), "ok"))


def _datos_northwind(con, rnd):
    paises = ["Germany", "France", "USA", "Brazil", "Argentina"]
    for i in range(1, 31):
        con.execute("INSERT INTO customers VALUES (?,?,?,?,?)",
                    (f"CUS{i:02d}", f"Company {i:02d}", f"Contact {i:02d}", f"City {i % 9}", paises[i % 5]))
    for e in range(1, 7):
        con.execute("INSERT INTO employees VALUES (?,?,?,?,?)",
                    (e, f"Last{e}", f"First{e}", rnd.choice(["Sales Representative", "Sales Manager"]), paises[e % 5]))
    for c, nom in enumerate(["Beverages", "Condiments", "Confections", "Seafood"], 1):
        con.execute("INSERT INTO categories VALUES (?,?,?)", (c, nom, f"Description of {nom}"))
    for s in range(1, 6):
        con.execute("INSERT INTO suppliers VALUES (?,?,?)", (s, f"Supplier {s}", paises[s % 5]))
    for s in range(1, 4):
        con.execute("INSERT INTO shippers VALUES (?,?,?)", (s, f"Shipper {s}", f"555-000{s}"))
    for p in range(1, 21):
        con.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?)",
                    (p, f"Product {p:02d}", rnd.randint(1, 5), rnd.randint(1, 4), round(rnd.uniform(5, 80), 2),
                     rnd.randint(0, 120), int(rnd.random() < 0.2)))
    for o in range(1, 161):
        # Los clientes 1-5 (Germany es paises[i % 5] con i múltiplo de 5) no compran en 1998.
        cli = rnd.randint(1, 30)
        anio = rnd.choice([1996, 1997, 1998])
        if anio == 1998 and cli % 5 == 0:
            anio = 1997
        fecha = f"{anio}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}"
        con.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)",
                    (o, f"CUS{cli:02d}", rnd.randint(1, 6), fecha, fecha, rnd.randint(1, 3),
                     round(rnd.uniform(1, 200), 2), paises[rnd.randint(0, 4)]))
        for p in rnd.sample(range(1, 21), rnd.randint(1, 4)):
            con.execute("INSERT INTO order_details VALUES (?,?,?,?,?)",
                        (o, p, round(rnd.uniform(5, 80), 2), rnd.randint(1, 30), rnd.choice([0, 0.05, 0.1])))


ESQUEMAS = [
    {
        "nombre": "cobranzas_es",
        "ddl": [
            "CREATE TABLE clientes (cliente_id INTEGER PRIMARY KEY, nombre VARCHAR(80), documento VARCHAR(20), "
            "ciudad VARCHAR(40), provincia VARCHAR(40), segmento TEXT, fecha_alta DATE, last_update TEXT)",
            "CREATE TABLE sucursales (sucursal_id INTEGER PRIMARY KEY, nombre TEXT, ciudad TEXT)",
            "CREATE TABLE creditos (credito_id INTEGER PRIMARY KEY, cliente_id INTEGER REFERENCES clientes(cliente_id), "
            "sucursal_id INTEGER REFERENCES sucursales(sucursal_id), monto_otorgado REAL, tasa_anual REAL, "
            "fecha_otorgamiento DATE, plazo_meses INTEGER, estado TEXT)",
            "CREATE TABLE cuotas (cuota_id INTEGER PRIMARY KEY, credito_id INTEGER REFERENCES creditos(credito_id), "
            "numero INTEGER, fecha_vencimiento DATE, importe REAL, pagada INTEGER)",
            "CREATE TABLE pagos (pago_id INTEGER PRIMARY KEY, cuota_id INTEGER REFERENCES cuotas(cuota_id), "
            "fecha_pago DATE, importe_pagado REAL, medio_pago TEXT)",
            "CREATE TABLE gestiones_cobranza (gestion_id INTEGER PRIMARY KEY, "
            "cliente_id INTEGER REFERENCES clientes(cliente_id), fecha_gestion DATE, canal TEXT, resultado TEXT, "
            "gestor TEXT)",
            "CREATE TABLE usuarios_sistema (usuario_id INTEGER PRIMARY KEY, login TEXT, rol TEXT, ultimo_acceso TEXT)",
            "CREATE TABLE parametros (clave TEXT PRIMARY KEY, valor TEXT, descripcion TEXT)",
        ],
        "datos": _datos_cobranzas,
        "preguntas": [
            ("¿Cuánto se cobró por sucursal en 2024?",
             "SELECT s.nombre AS sucursal, SUM(p.importe_pagado) AS total_cobrado FROM pagos p "
             "JOIN cuotas cu ON cu.cuota_id = p.cuota_id JOIN creditos cr ON cr.credito_id = cu.credito_id "
             "JOIN sucursales s ON s.sucursal_id = cr.sucursal_id "
             "WHERE p.fecha_pago >= '2024-01-01' AND p.fecha_pago < '2025-01-01' "
             "GROUP BY s.nombre ORDER BY total_cobrado DESC",
             ["pagos", "cuotas", "creditos", "sucursales"]),
            ("Top 10 clientes con mayor deuda vencida",
             "WITH deuda AS (SELECT cr.cliente_id, SUM(cu.importe) AS deuda_vencida FROM cuotas cu "
             "JOIN creditos cr ON cr.credito_id = cu.credito_id "
             "WHERE cu.pagada = 0 AND cu.fecha_vencimiento < '2025-01-01' GROUP BY cr.cliente_id) "
             "SELECT c.nombre, d.deuda_vencida FROM deuda d JOIN clientes c ON c.cliente_id = d.cliente_id "
             "ORDER BY d.deuda_vencida DESC LIMIT 10",
             ["cuotas", "creditos", "clientes"]),
            ("How many credits were granted per branch?",
             "SELECT s.nombre AS branch, COUNT(cr.credito_id) AS credits FROM creditos cr "
             "JOIN sucursales s ON s.sucursal_id = cr.sucursal_id GROUP BY s.nombre",
             ["creditos", "sucursales"]),
            ("Quantos pagamentos foram feitos por meio de pagamento em 2024?",
             "SELECT medio_pago, COUNT(*) AS pagamentos FROM pagos "
             "WHERE fecha_pago >= '2024-01-01' AND fecha_pago < '2025-01-01' GROUP BY medio_pago",
             ["pagos"]),
            ("Promedio de tasa anual de los créditos por segmento de cliente",
             "SELECT c.segmento, AVG(cr.tasa_anual) AS tasa_promedio FROM creditos cr "
             "JOIN clientes c ON c.cliente_id = cr.cliente_id GROUP BY c.segmento",
             ["creditos", "clientes"]),
            ("Resultado de las gestiones de cobranza a clientes de Córdoba",
             "SELECT g.resultado, COUNT(*) AS gestiones FROM gestiones_cobranza g "
             "JOIN clientes c ON c.cliente_id = g.cliente_id WHERE c.ciudad = 'Córdoba' GROUP BY g.resultado",
             ["gestiones_cobranza", "clientes"]),
            ("Monto total otorgado por mes en 2024",
             "SELECT strftime('%Y-%m', fecha_otorgamiento) AS mes, SUM(monto_otorgado) AS total_otorgado "
             "FROM creditos WHERE fecha_otorgamiento >= '2024-01-01' AND fecha_otorgamiento < '2025-01-01' "
             "GROUP BY mes ORDER BY mes",
             ["creditos"]),
            ("Qual é o valor total das parcelas vencidas e não pagas por agência?",
             "SELECT s.nombre AS agencia, SUM(cu.importe) AS valor_vencido FROM cuotas cu "
             "JOIN creditos cr ON cr.credito_id = cu.credito_id JOIN sucursales s ON s.sucursal_id = cr.sucursal_id "
             "WHERE cu.pagada = 0 AND cu.fecha_vencimiento < '2025-01-01' GROUP BY s.nombre",
             ["cuotas", "creditos", "sucursales"]),
            ("¿Qué gestor hizo más gestiones en 2024?",
             "SELECT gestor, COUNT(*) AS gestiones FROM gestiones_cobranza "
             "WHERE fecha_gestion >= '2024-01-01' AND fecha_gestion < '2025-01-01' "
             "GROUP BY gestor ORDER BY gestiones DESC LIMIT 1",
             ["gestiones_cobranza"]),
            ("Clientes actualizados en 2024 y su última actualización",
             "SELECT c.nombre, c.last_update FROM clientes c WHERE c.last_update >= '2024-01-01' "
             "ORDER BY c.last_update DESC",
             ["clientes"]),
        ],
        "alucinados": [
            "SELECT c.nombre_completo FROM clientes c",                       # columna inexistente
            "SELECT SUM(monto_cobrado) AS total FROM pagos",                  # inexistente, sin alias
            "SELECT p.ciudad, SUM(p.importe_pagado) AS t FROM pagos p GROUP BY p.ciudad",  # de otra tabla
            "SELECT ciudad, SUM(importe_pagado) AS t FROM pagos GROUP BY ciudad",          # de otra tabla, sin alias
            "SELECT nombre FROM cobradores",                                  # tabla inexistente
        ],
    },
    {
        "nombre": "retail_en",
        "ddl": [
            "CREATE TABLE FactSales (SalesKey INTEGER, DateKey INTEGER, CustomerKey INTEGER, ProductKey INTEGER, "
            "StoreKey INTEGER, Quantity INTEGER, UnitPrice REAL, SalesAmount REAL, DiscountAmount REAL, "
            "CostAmount REAL)",
            "CREATE TABLE DimCustomer (CustomerKey INTEGER, CustomerName TEXT, City TEXT, Country TEXT, Segment TEXT)",
            "CREATE TABLE DimProduct (ProductKey INTEGER, ProductName TEXT, Category TEXT, Subcategory TEXT, "
            "Brand TEXT)",
            "CREATE TABLE DimDate (DateKey INTEGER, FullDate TEXT, Year INTEGER, MonthNumber INTEGER, "
            "MonthName TEXT, Quarter TEXT)",
            "CREATE TABLE DimStore (StoreKey INTEGER, StoreName TEXT, Region TEXT, City TEXT)",
            "CREATE TABLE FactInventory (DateKey INTEGER, ProductKey INTEGER, StoreKey INTEGER, StockOnHand INTEGER)",
            "CREATE TABLE AuditLog (LogId INTEGER, EventTime TEXT, UserName TEXT, Action TEXT)",
        ],
        "datos": _datos_retail,
        "preguntas": [
            ("ventas por cliente en 2024",
             "SELECT c.CustomerName, SUM(f.SalesAmount) AS ventas FROM FactSales f "
             "JOIN DimCustomer c ON c.CustomerKey = f.CustomerKey JOIN DimDate d ON d.DateKey = f.DateKey "
             "WHERE d.Year = 2024 GROUP BY c.CustomerName",
             ["FactSales", "DimCustomer", "DimDate"]),
            ("sales by customer",
             "SELECT c.CustomerName, SUM(f.SalesAmount) AS sales FROM FactSales f "
             "JOIN DimCustomer c ON c.CustomerKey = f.CustomerKey GROUP BY c.CustomerName",
             ["FactSales", "DimCustomer"]),
            ("Top 5 productos por margen en 2024",
             "SELECT p.ProductName, SUM(f.SalesAmount - f.CostAmount) AS margen FROM FactSales f "
             "JOIN DimProduct p ON p.ProductKey = f.ProductKey JOIN DimDate d ON d.DateKey = f.DateKey "
             "WHERE d.Year = 2024 GROUP BY p.ProductName ORDER BY margen DESC LIMIT 5",
             ["FactSales", "DimProduct", "DimDate"]),
            ("Vendas por região e trimestre",
             "SELECT s.Region, d.Quarter, SUM(f.SalesAmount) AS vendas FROM FactSales f "
             "JOIN DimStore s ON s.StoreKey = f.StoreKey JOIN DimDate d ON d.DateKey = f.DateKey "
             "GROUP BY s.Region, d.Quarter",
             ["FactSales", "DimStore", "DimDate"]),
            ("Stock actual por tienda y categoría",
             "SELECT s.StoreName, p.Category, SUM(i.StockOnHand) AS stock FROM FactInventory i "
             "JOIN DimStore s ON s.StoreKey = i.StoreKey JOIN DimProduct p ON p.ProductKey = i.ProductKey "
             "GROUP BY s.StoreName, p.Category",
             ["FactInventory", "DimStore", "DimProduct"]),
            ("What was the total discount by brand?",
             "SELECT p.Brand, SUM(f.DiscountAmount) AS total_discount FROM FactSales f "
             "JOIN DimProduct p ON p.ProductKey = f.ProductKey GROUP BY p.Brand",
             ["FactSales", "DimProduct"]),
            ("Cantidad vendida por país del cliente",
             "SELECT c.Country, SUM(f.Quantity) AS cantidad FROM FactSales f "
             "JOIN DimCustomer c ON c.CustomerKey = f.CustomerKey GROUP BY c.Country",
             ["FactSales", "DimCustomer"]),
            ("Monthly revenue in 2024",
             "SELECT d.MonthNumber, SUM(f.SalesAmount) AS revenue FROM FactSales f "
             "JOIN DimDate d ON d.DateKey = f.DateKey WHERE d.Year = 2024 GROUP BY d.MonthNumber "
             "ORDER BY d.MonthNumber",
             ["FactSales", "DimDate"]),
            ("Ticket promedio por segmento de cliente",
             "SELECT c.Segment, AVG(f.SalesAmount) AS ticket_promedio FROM FactSales f "
             "JOIN DimCustomer c ON c.CustomerKey = f.CustomerKey GROUP BY c.Segment",
             ["FactSales", "DimCustomer"]),
            ("Average unit price by subcategory",
             "SELECT p.Subcategory, AVG(f.UnitPrice) AS avg_unit_price FROM FactSales f "
             "JOIN DimProduct p ON p.ProductKey = f.ProductKey GROUP BY p.Subcategory",
             ["FactSales", "DimProduct"]),
        ],
        "alucinados": [
            "SELECT c.CustomerEmail FROM DimCustomer c",
            "SELECT SUM(NetRevenue) AS total FROM FactSales",
            "SELECT f.Category, SUM(f.SalesAmount) AS t FROM FactSales f GROUP BY f.Category",
            "SELECT Region, SUM(SalesAmount) AS t FROM FactSales GROUP BY Region",
            "SELECT EmployeeName FROM DimEmployee",
        ],
    },
    {
        "nombre": "erp_es",
        "ddl": [
            "CREATE TABLE clientes (cod_cliente TEXT PRIMARY KEY, razon_social VARCHAR(80), cuit VARCHAR(13), "
            "localidad VARCHAR(40), provincia NVARCHAR(40), condicion_iva CHAR(2))",
            "CREATE TABLE articulos (cod_articulo TEXT PRIMARY KEY, descripcion VARCHAR(100), rubro VARCHAR(30), "
            "precio_lista DECIMAL(12,2), costo DECIMAL(12,2))",
            "CREATE TABLE vendedores (cod_vendedor TEXT PRIMARY KEY, nombre VARCHAR(60), zona VARCHAR(20))",
            'CREATE TABLE "order" (nro_pedido INTEGER PRIMARY KEY, cod_cliente TEXT, cod_vendedor TEXT, '
            "fecha_pedido DATE, estado CHAR(1))",
            "CREATE TABLE pedido_items (nro_pedido INTEGER, renglon INTEGER, cod_articulo TEXT, cantidad INTEGER, "
            "precio_unitario DECIMAL(12,2), PRIMARY KEY (nro_pedido, renglon))",
            "CREATE TABLE facturas (nro_factura INTEGER PRIMARY KEY, nro_pedido INTEGER, cod_cliente TEXT, "
            "fecha_emision DATE, importe_neto DECIMAL(14,2), importe_iva DECIMAL(14,2))",
            'CREATE TABLE "Ventas Mensuales" (periodo CHAR(7), cod_vendedor TEXT, cod_articulo TEXT, '
            "unidades INTEGER, importe DECIMAL(14,2))",
            "CREATE TABLE log_sincronizacion (id INTEGER PRIMARY KEY, fecha DATETIME, detalle TEXT)",
        ],
        "datos": _datos_erp,
        "preguntas": [
            ("Importe facturado por provincia en 2024",
             "SELECT c.provincia, SUM(f.importe_neto) AS facturado FROM facturas f "
             "JOIN clientes c ON c.cod_cliente = f.cod_cliente "
             "WHERE f.fecha_emision >= '2024-01-01' AND f.fecha_emision < '2025-01-01' GROUP BY c.provincia",
             ["facturas", "clientes"]),
            ("Unidades vendidas por rubro en el período 2024-03",
             'SELECT a.rubro, SUM(vm.unidades) AS unidades FROM "Ventas Mensuales" vm '
             "JOIN articulos a ON a.cod_articulo = vm.cod_articulo WHERE vm.periodo = '2024-03' GROUP BY a.rubro",
             ["Ventas Mensuales", "articulos"]),
            ("Ranking de vendedores por importe de ventas mensuales en 2024",
             'SELECT v.nombre, SUM(vm.importe) AS importe FROM "Ventas Mensuales" vm '
             "JOIN vendedores v ON v.cod_vendedor = vm.cod_vendedor WHERE vm.periodo LIKE '2024-%' "
             "GROUP BY v.nombre ORDER BY importe DESC",
             ["Ventas Mensuales", "vendedores"]),
            ("How many orders per salesperson zone?",
             'SELECT v.zona, COUNT(o.nro_pedido) AS orders FROM "order" o '
             "JOIN vendedores v ON v.cod_vendedor = o.cod_vendedor GROUP BY v.zona",
             ["order", "vendedores"]),
            ("Quais clientes fizeram mais pedidos?",
             'SELECT c.razon_social, COUNT(*) AS pedidos FROM "order" o '
             "JOIN clientes c ON c.cod_cliente = o.cod_cliente GROUP BY c.razon_social "
             "ORDER BY pedidos DESC LIMIT 10",
             ["order", "clientes"]),
            ("Margen bruto por artículo en las líneas de pedido",
             "SELECT a.descripcion, SUM(i.cantidad * (i.precio_unitario - a.costo)) AS margen_bruto "
             "FROM pedido_items i JOIN articulos a ON a.cod_articulo = i.cod_articulo "
             "GROUP BY a.descripcion ORDER BY margen_bruto DESC",
             ["pedido_items", "articulos"]),
            ("Pedidos pendientes con su cliente y vendedor",
             'SELECT o.nro_pedido, c.razon_social, v.nombre AS vendedor FROM "order" o '
             "JOIN clientes c ON c.cod_cliente = o.cod_cliente "
             "JOIN vendedores v ON v.cod_vendedor = o.cod_vendedor WHERE o.estado = 'P'",
             ["order", "clientes", "vendedores"]),
            ("Facturas por mes de clientes responsables inscriptos",
             "SELECT strftime('%Y-%m', f.fecha_emision) AS mes, COUNT(*) AS facturas FROM facturas f "
             "JOIN clientes c ON c.cod_cliente = f.cod_cliente WHERE c.condicion_iva = 'RI' "
             "GROUP BY mes ORDER BY mes",
             ["facturas", "clientes"]),
            ("Total facturado por vendedor",
             'SELECT v.nombre, SUM(f.importe_neto) AS total_facturado FROM facturas f '
             'JOIN "order" o ON o.nro_pedido = f.nro_pedido '
             "JOIN vendedores v ON v.cod_vendedor = o.cod_vendedor GROUP BY v.nombre",
             ["facturas", "order", "vendedores"]),
            ("Precio de lista promedio por rubro, sin los artículos de Drop Shipping",
             "SELECT rubro, AVG(precio_lista) AS precio_promedio FROM articulos "
             "WHERE rubro <> 'Drop Shipping' GROUP BY rubro",
             ["articulos"]),
        ],
        "alucinados": [
            "SELECT c.email FROM clientes c",
            "SELECT SUM(importe_total) AS total FROM facturas",
            "SELECT f.zona, SUM(f.importe_neto) AS t FROM facturas f GROUP BY f.zona",
            "SELECT rubro, SUM(importe_neto) AS t FROM facturas GROUP BY rubro",
            "SELECT nro_pedido FROM pedidos",
        ],
    },
    {
        "nombre": "northwind_en",
        "ddl": [
            "CREATE TABLE customers (CustomerID TEXT PRIMARY KEY, CompanyName TEXT, ContactName TEXT, City TEXT, "
            "Country TEXT)",
            "CREATE TABLE employees (EmployeeID INTEGER PRIMARY KEY, LastName TEXT, FirstName TEXT, Title TEXT, "
            "Country TEXT)",
            "CREATE TABLE orders (OrderID INTEGER PRIMARY KEY, CustomerID TEXT, EmployeeID INTEGER, OrderDate TEXT, "
            "ShippedDate TEXT, ShipVia INTEGER, Freight REAL, ShipCountry TEXT)",
            "CREATE TABLE order_details (OrderID INTEGER, ProductID INTEGER, UnitPrice REAL, Quantity INTEGER, "
            "Discount REAL, PRIMARY KEY (OrderID, ProductID))",
            "CREATE TABLE products (ProductID INTEGER PRIMARY KEY, ProductName TEXT, SupplierID INTEGER, "
            "CategoryID INTEGER, UnitPrice REAL, UnitsInStock INTEGER, Discontinued INTEGER)",
            "CREATE TABLE categories (CategoryID INTEGER PRIMARY KEY, CategoryName TEXT, Description TEXT)",
            "CREATE TABLE suppliers (SupplierID INTEGER PRIMARY KEY, CompanyName TEXT, Country TEXT)",
            "CREATE TABLE shippers (ShipperID INTEGER PRIMARY KEY, CompanyName TEXT, Phone TEXT)",
        ],
        "datos": _datos_northwind,
        "preguntas": [
            ("Sales by customer",
             "SELECT c.CompanyName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS sales "
             "FROM customers c JOIN orders o ON o.CustomerID = c.CustomerID "
             "JOIN order_details od ON od.OrderID = o.OrderID GROUP BY c.CompanyName ORDER BY sales DESC",
             ["customers", "orders", "order_details"]),
            ("Ventas por categoría en 1997",
             "SELECT cat.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS ventas "
             "FROM order_details od JOIN orders o ON o.OrderID = od.OrderID "
             "JOIN products p ON p.ProductID = od.ProductID JOIN categories cat ON cat.CategoryID = p.CategoryID "
             "WHERE o.OrderDate >= '1997-01-01' AND o.OrderDate < '1998-01-01' GROUP BY cat.CategoryName",
             ["order_details", "orders", "products", "categories"]),
            ("Quantos pedidos cada funcionário atendeu?",
             "SELECT e.FirstName, e.LastName, COUNT(o.OrderID) AS pedidos FROM employees e "
             "JOIN orders o ON o.EmployeeID = e.EmployeeID GROUP BY e.EmployeeID, e.FirstName, e.LastName",
             ["employees", "orders"]),
            ("Top 10 products by quantity sold",
             "SELECT p.ProductName, SUM(od.Quantity) AS quantity_sold FROM order_details od "
             "JOIN products p ON p.ProductID = od.ProductID GROUP BY p.ProductName "
             "ORDER BY quantity_sold DESC LIMIT 10",
             ["order_details", "products"]),
            ("Proveedores con productos discontinuados",
             "SELECT s.CompanyName, COUNT(*) AS discontinuados FROM suppliers s "
             "JOIN products p ON p.SupplierID = s.SupplierID WHERE p.Discontinued = 1 GROUP BY s.CompanyName",
             ["suppliers", "products"]),
            ("Average freight by ship country",
             "SELECT ShipCountry, AVG(Freight) AS avg_freight FROM orders GROUP BY ShipCountry",
             ["orders"]),
            ("Clientes de Alemania sin pedidos en 1998",
             "SELECT c.CompanyName FROM customers c WHERE c.Country = 'Germany' AND NOT EXISTS "
             "(SELECT 1 FROM orders o WHERE o.CustomerID = c.CustomerID "
             "AND o.OrderDate >= '1998-01-01' AND o.OrderDate < '1999-01-01')",
             ["customers", "orders"]),
            ("Stock por categoría",
             "SELECT cat.CategoryName, SUM(p.UnitsInStock) AS stock FROM products p "
             "JOIN categories cat ON cat.CategoryID = p.CategoryID GROUP BY cat.CategoryName",
             ["products", "categories"]),
            ("Receita por país do cliente em 1997",
             "SELECT c.Country, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS receita "
             "FROM customers c JOIN orders o ON o.CustomerID = c.CustomerID "
             "JOIN order_details od ON od.OrderID = o.OrderID "
             "WHERE o.OrderDate >= '1997-01-01' AND o.OrderDate < '1998-01-01' GROUP BY c.Country",
             ["customers", "orders", "order_details"]),
            ("Which employee sold the most in 1997?",
             "WITH ventas_emp AS (SELECT o.EmployeeID, SUM(od.UnitPrice * od.Quantity) AS total FROM orders o "
             "JOIN order_details od ON od.OrderID = o.OrderID "
             "WHERE o.OrderDate >= '1997-01-01' AND o.OrderDate < '1998-01-01' GROUP BY o.EmployeeID) "
             "SELECT e.FirstName, e.LastName, v.total FROM ventas_emp v "
             "JOIN employees e ON e.EmployeeID = v.EmployeeID ORDER BY v.total DESC LIMIT 1",
             ["orders", "order_details", "employees"]),
            ("Pedidos por mes de 1997, incluidos los meses sin pedidos",
             "WITH RECURSIVE meses(m) AS (SELECT 1 UNION ALL SELECT m + 1 FROM meses WHERE m < 12) "
             "SELECT meses.m AS mes, COUNT(o.OrderID) AS pedidos FROM meses "
             "LEFT JOIN orders o ON CAST(strftime('%m', o.OrderDate) AS INTEGER) = meses.m "
             "AND o.OrderDate >= '1997-01-01' AND o.OrderDate < '1998-01-01' "
             "GROUP BY meses.m ORDER BY meses.m",
             ["orders"]),
        ],
        "alucinados": [
            "SELECT c.Email FROM customers c",
            "SELECT SUM(TotalAmount) AS total FROM orders",
            "SELECT o.ProductName, COUNT(*) AS n FROM orders o GROUP BY o.ProductName",
            "SELECT CategoryName, SUM(Freight) AS t FROM orders GROUP BY CategoryName",
            "SELECT * FROM customer",
        ],
    },
]


# ══════════════════════════════════════════════════════════════
# Medición
# ══════════════════════════════════════════════════════════════
def _limpio(nombre):
    return str(nombre).split(".")[-1].strip().strip('[]"`').lower()


def _crear_base(esquema, carpeta):
    ruta = os.path.join(carpeta, esquema["nombre"] + ".db")
    con = sqlite3.connect(ruta)
    for ddl in esquema["ddl"]:
        con.execute(ddl)
    esquema["datos"](con, random.Random(20261013))
    con.commit()
    con.close()
    return ruta


def _joins_de(sql):
    """Los JOIN ... ON verificables del SQL: [(tabla_a, col_a, tabla_b, col_b)]."""
    salida = []
    for j in control_resultado.joins_del_sql(sql):
        if not j["verificable"]:
            continue
        for cb, cu in zip(j["col_base"], j["col_unida"]):
            salida.append((_limpio(j["base"]), _limpio(cb), _limpio(j["unida"]), _limpio(cu)))
    return salida


def _join_en_mapa(cat, mapa, a, ca, b, cb):
    if MS is not None:
        return MS.relacion_entre(mapa, a, ca, b, cb) is not None
    # Código anterior: lo único que había eran las FKs y `joins_inferidos`
    # ({columna: [tablas que la comparten]}).
    for fk in cat.get("fks", []):
        par = (_limpio(fk.get("tabla_origen", "")), _limpio(fk.get("columna_origen", "")),
               _limpio(fk.get("tabla_destino", "")), _limpio(fk.get("columna_destino", "")))
        if par in ((a, ca, b, cb), (b, cb, a, ca)):
            return True
    if ca == cb:
        for col, tablas in cat.get("joins_inferidos", {}).items():
            if col.lower() == ca and {a, b} <= {t.lower() for t in tablas}:
                return True
    return False


def _join_en_prompt(system, a, ca, b, cb):
    """¿Hay una línea del prompt que nombre las dos puntas del JOIN?"""
    for linea in system.lower().replace('"', "").replace("[", "").replace("]", "").replace("`", "").splitlines():
        if f"{a}.{ca}" in linea and f"{b}.{cb}" in linea:
            return True
    return False


def _confianza(conf_llm, sim, valido, n_adv, usa_cte, cobertura, ejec, joins):
    extra = {"joins_validos": joins} if _JOINS_EN_CONFIANZA else {}
    return motor.calcular_confianza(conf_llm, sim, valido, n_adv, usa_cte, cobertura=cobertura,
                                    ejecucion=ejec, **extra)


def _joins_validos(sql, mapa):
    return MS.joins_validos(sql, mapa) if MS is not None else None


def medir(esquema, carpeta):
    m = {"carga": True, "error_carga": None, "n_tablas": len(esquema["ddl"]),
         "tablas_oro": 0, "tablas_ok": 0, "preg": 0, "preg_completas": 0, "recuperadas": 0,
         "oro_validos": 0, "oro_ejecuta": 0, "oro_adv": 0, "rechazos_falsos": [],
         "aluc": 0, "aluc_detectados": 0, "aluc_no_detectados": [],
         "joins": 0, "joins_mapa": 0, "joins_prompt": 0, "joins_faltan": [],
         "conf_oro": [], "conf_invalido": [], "conf_error": [], "conf_vacio_menor": True,
         "conf_monotona": True, "faltan_rag": []}
    ruta = _crear_base(esquema, carpeta)
    try:
        cx = ConexionBD("sqlite", ruta=ruta).conectar()
        mv = motor.MotorMVSQL(cx, {"proveedor": "oraculo"})
    except Exception as e:                       # el catálogo ni siquiera carga
        m.update(carga=False, error_carga=f"{type(e).__name__}: {e}")
        n = len(esquema["preguntas"])
        m.update(preg=n, tablas_oro=sum(len(p[2]) for p in esquema["preguntas"]),
                 aluc=len(esquema["alucinados"]))
        m["joins"] = sum(len(_joins_de(p[1])) for p in esquema["preguntas"])
        return m
    cat = mv.catalogo
    mapa = MS.construir_mapa(cat) if MS is not None else None

    for pregunta, oro, tablas in esquema["preguntas"]:
        prompts = []

        def oraculo(system, user, max_tokens=1500, _oro=oro):
            prompts.append(system)
            return f"SQL:\n{_oro}\nCONFIANZA: {CONF_LLM_ORO}\nSUPUESTOS: ninguno"

        mv._completar = oraculo
        r = mv.responder(pregunta, explicar=False)
        recuperadas = {_limpio(t) for t in r["tablas_recuperadas"]}
        necesarias = {_limpio(t) for t in tablas}
        m["preg"] += 1
        m["recuperadas"] += len(recuperadas)
        m["tablas_oro"] += len(necesarias)
        m["tablas_ok"] += len(necesarias & recuperadas)
        if necesarias <= recuperadas:
            m["preg_completas"] += 1
        else:
            m["faltan_rag"].append(f"{pregunta!r}: faltan {sorted(necesarias - recuperadas)}")

        ok, problemas, adv = motor.validar_sql(oro, cat)
        if ok:
            m["oro_validos"] += 1
        else:
            m["rechazos_falsos"].append(f"{pregunta!r}: {problemas}")
        m["oro_adv"] += len(adv)
        if r["error"] is None and r["filas"]:
            m["oro_ejecuta"] += 1
        elif r["error"]:
            m["rechazos_falsos"].append(f"{pregunta!r}: error al ejecutar: {r['error']}")

        system = prompts[0] if prompts else ""
        for a, ca, b, cb in _joins_de(oro):
            m["joins"] += 1
            if _join_en_mapa(cat, mapa, a, ca, b, cb):
                m["joins_mapa"] += 1
            else:
                m["joins_faltan"].append(f"{a}.{ca} = {b}.{cb}")
            if _join_en_prompt(system, a, ca, b, cb):
                m["joins_prompt"] += 1

        if r["confianza"]:
            m["conf_oro"].append(r["confianza"]["puntaje"])
        # (v) misma consulta, otras señales: monotonía y vacío < ok
        sim = 0.3
        jv = _joins_validos(oro, mapa)
        ok_c = _confianza(CONF_LLM_ORO, sim, True, 0, False, 1.0, "ok", jv)["puntaje"]
        vac_c = _confianza(CONF_LLM_ORO, sim, True, 0, False, 1.0, "vacio", jv)["puntaje"]
        if not vac_c < ok_c:
            m["conf_vacio_menor"] = False
        serie = [_confianza(c, sim, True, 0, False, 1.0, "ok", jv)["puntaje"] for c in range(0, 101, 10)]
        if any(b < a for a, b in zip(serie, serie[1:])):
            m["conf_monotona"] = False
        m["conf_error"].append(_confianza(99, sim, True, 0, False, 1.0, "error", jv)["puntaje"])

    for sql in esquema["alucinados"]:
        m["aluc"] += 1
        ok, problemas, adv = motor.validar_sql(sql, cat)
        if not ok or adv:
            m["aluc_detectados"] += 1
        else:
            m["aluc_no_detectados"].append(sql)
        if not ok:
            # Un SQL rechazado nunca se ejecuta: la confianza no puede ser alta
            # aunque el modelo diga 90.
            m["conf_invalido"].append(_confianza(90, 0.3, False, len(adv), False, 1.0, None, None)["puntaje"])
    cx.cerrar()
    return m


def _pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "  —  "


def _tabla(resultados):
    nombres = [e["nombre"] for e in ESQUEMAS]
    glob = {k: sum(r[k] for r in resultados.values()) for k in
            ("tablas_oro", "tablas_ok", "preg", "preg_completas", "recuperadas", "oro_validos",
             "oro_ejecuta", "oro_adv", "aluc", "aluc_detectados", "joins", "joins_mapa", "joins_prompt")}
    filas = [
        ("catálogo carga", lambda r: "sí" if r["carga"] else "NO", "—"),
        ("(i) recall de tablas del oro", lambda r: _pct(r["tablas_ok"], r["tablas_oro"]),
         _pct(glob["tablas_ok"], glob["tablas_oro"])),
        ("(i) preguntas con TODAS sus tablas", lambda r: f"{r['preg_completas']}/{r['preg']}",
         f"{glob['preg_completas']}/{glob['preg']}"),
        ("(i) tablas recuperadas por pregunta", lambda r: (f"{r['recuperadas'] / r['preg']:.1f} de {r['n_tablas']}"
                                                         if r["carga"] else "—"), "—"),
        ("(ii) oro valida (sin rechazo falso)", lambda r: f"{r['oro_validos']}/{r['preg']}",
         f"{glob['oro_validos']}/{glob['preg']}"),
        ("(ii) oro ejecuta con filas", lambda r: f"{r['oro_ejecuta']}/{r['preg']}",
         f"{glob['oro_ejecuta']}/{glob['preg']}"),
        ("(ii) advertencias falsas sobre el oro", lambda r: str(r["oro_adv"]), str(glob["oro_adv"])),
        ("(iii) alucinados detectados", lambda r: f"{r['aluc_detectados']}/{r['aluc']}",
         f"{glob['aluc_detectados']}/{glob['aluc']}"),
        ("(iv) JOINs del oro en el mapa", lambda r: f"{r['joins_mapa']}/{r['joins']}",
         f"{glob['joins_mapa']}/{glob['joins']} ({_pct(glob['joins_mapa'], glob['joins']).strip()})"),
        ("(iv) JOINs del oro en el prompt", lambda r: f"{r['joins_prompt']}/{r['joins']}",
         f"{glob['joins_prompt']}/{glob['joins']} ({_pct(glob['joins_prompt'], glob['joins']).strip()})"),
        ("(v) confianza del oro (mín)", lambda r: str(min(r["conf_oro"])) if r["conf_oro"] else "—",
         str(min(sum((r["conf_oro"] for r in resultados.values()), []) or [0]))),
        ("(v) confianza SQL rechazado (máx)", lambda r: str(max(r["conf_invalido"])) if r["conf_invalido"] else "—",
         str(max(sum((r["conf_invalido"] for r in resultados.values()), []) or [0]))),
        ("(v) confianza con error (máx)", lambda r: str(max(r["conf_error"])) if r["conf_error"] else "—",
         str(max(sum((r["conf_error"] for r in resultados.values()), []) or [0]))),
        ("(v) vacío < ok · monotonía", lambda r: ("sí" if r["conf_vacio_menor"] else "NO") + " · "
         + ("sí" if r["conf_monotona"] else "NO"), "—"),
    ]
    ancho = 38
    cols = [max(14, len(n) + 2) for n in nombres]
    print("\n  " + "métrica".ljust(ancho) + "".join(n.ljust(c) for n, c in zip(nombres, cols)) + "GLOBAL")
    print("  " + "─" * (ancho + sum(cols) + 18))
    for etiqueta, fn, total in filas:
        print("  " + etiqueta.ljust(ancho) + "".join(fn(resultados[n]).ljust(c) for n, c in zip(nombres, cols))
              + total)
    print()
    for n in nombres:
        r = resultados[n]
        if r["error_carga"]:
            print(f"  [{n}] el catálogo no carga: {r['error_carga']}")
        for linea in r["faltan_rag"]:
            print(f"  [{n}] RAG {linea}")
        for linea in r["rechazos_falsos"]:
            print(f"  [{n}] oro rechazado/no ejecuta {linea}")
        for linea in r["aluc_no_detectados"]:
            print(f"  [{n}] alucinado NO detectado: {linea}")
        for linea in r["joins_faltan"]:
            print(f"  [{n}] JOIN fuera del mapa: {linea}")
    return glob


print("\n== Banco de esquemas: métricas ==")
_carpeta = tempfile.mkdtemp(prefix="banco_esquemas_")
RES = {e["nombre"]: medir(e, _carpeta) for e in ESQUEMAS}
GLOBAL = _tabla(RES)
TODAS_CONF_ORO = sum((r["conf_oro"] for r in RES.values()), [])

print("== Lo que se exige ==")


@test("los cuatro catálogos cargan (nombres con espacio y palabras reservadas incluidos)")
def _():
    malos = {n: r["error_carga"] for n, r in RES.items() if not r["carga"]}
    assert not malos, malos


@test("(i) recall de tablas del RAG ≥ 95 % global")
def _():
    rec = GLOBAL["tablas_ok"] / GLOBAL["tablas_oro"]
    assert rec >= 0.95, f"{rec:.1%}"


@test("(i) el RAG no manda todo el esquema: en promedio menos tablas que las que hay")
def _():
    for n, r in RES.items():
        assert r["recuperadas"] / r["preg"] < r["n_tablas"], (n, r["recuperadas"] / r["preg"], r["n_tablas"])


@test("(ii) el SQL de oro valida: 0 rechazos falsos, y ejecuta con filas")
def _():
    assert GLOBAL["oro_validos"] == GLOBAL["preg"], [x for r in RES.values() for x in r["rechazos_falsos"]]
    assert GLOBAL["oro_ejecuta"] == GLOBAL["preg"], [x for r in RES.values() for x in r["rechazos_falsos"]]


@test("(ii) el SQL de oro no genera advertencias falsas")
def _():
    assert GLOBAL["oro_adv"] == 0, GLOBAL["oro_adv"]


@test("(iii) todo SQL alucinado sale rechazado o con advertencia")
def _():
    assert GLOBAL["aluc_detectados"] == GLOBAL["aluc"], [x for r in RES.values() for x in r["aluc_no_detectados"]]


@test("(iv) cada JOIN del oro está en el mapa semántico (100 %)")
def _():
    assert GLOBAL["joins"] > 20, GLOBAL["joins"]
    assert GLOBAL["joins_mapa"] == GLOBAL["joins"], [x for r in RES.values() for x in r["joins_faltan"]]


@test("(iv) y llega al prompt de generación")
def _():
    assert GLOBAL["joins_prompt"] == GLOBAL["joins"], f"{GLOBAL['joins_prompt']}/{GLOBAL['joins']}"


@test("(v) oro + LLM 80 + ejecución ok + JOINs del mapa → confianza ≥ 80")
def _():
    assert TODAS_CONF_ORO and min(TODAS_CONF_ORO) >= 80, sorted(TODAS_CONF_ORO)[:5]


@test("(v) SQL rechazado → ≤ 30 aunque el modelo diga 90")
def _():
    vals = sum((r["conf_invalido"] for r in RES.values()), [])
    assert vals and max(vals) <= 30, vals


@test("(v) error de ejecución → ≤ 35")
def _():
    assert max(sum((r["conf_error"] for r in RES.values()), [])) <= 35


@test("(v) vacío < ok y la confianza no baja cuando el modelo está más seguro")
def _():
    assert all(r["conf_vacio_menor"] and r["conf_monotona"] for r in RES.values())


@test("(v) más evidencia, intervalo más angosto; JOINs fuera del mapa bajan el puntaje")
def _():
    assert _JOINS_EN_CONFIANZA, "calcular_confianza no recibe joins_validos"
    sin_correr = motor.calcular_confianza(80, 0.3, True, 0, False, cobertura=1.0)
    corrida = motor.calcular_confianza(80, 0.3, True, 0, False, cobertura=1.0, ejecucion="ok")
    con_joins = motor.calcular_confianza(80, 0.3, True, 0, False, cobertura=1.0, ejecucion="ok",
                                         joins_validos=1.0)
    assert con_joins["margen"] <= corrida["margen"] < sin_correr["margen"], (con_joins, corrida, sin_correr)
    p = [motor.calcular_confianza(80, 0.3, True, 0, False, cobertura=1.0, ejecucion="ok",
                                  joins_validos=j)["puntaje"] for j in (0.0, 0.5, 1.0)]
    assert p[0] < p[1] < p[2], p


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
