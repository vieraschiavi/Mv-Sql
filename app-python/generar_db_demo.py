"""
generar_db_demo.py
==================================================================
Genera una base de datos SQLite sintetica de CARTERA / COBRANZAS
para probar el sistema NL2SQL + RAG.

Modelo de datos generico (inspirado en una financiera de creditos,
SIN nombres reales de ninguna empresa):

  clientes            -> datos demograficos
  operaciones         -> prestamos otorgados (1 cliente N operaciones)
  cuotas              -> detalle de cuotas por operacion
  gestiones           -> intentos de contacto (llamadas, whatsapp, email)
  arreglos_pago       -> refinanciaciones / acuerdos de pago
  estados_cliente     -> catalogo de estados (Comercial / Cobranzas / Juridica)

Ejecutar:  python generar_db_demo.py
Salida:    cartera_demo.db  (SQLite)
==================================================================
"""

import sqlite3
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("es_ES")
random.seed(42)
Faker.seed(42)

DB_PATH = "cartera_demo.db"
N_CLIENTES = 2000
FECHA_BASE = datetime(2024, 1, 1)
FECHA_HOY = datetime(2026, 6, 30)


def crear_esquema(con):
    cur = con.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS cuotas;
    DROP TABLE IF EXISTS gestiones;
    DROP TABLE IF EXISTS arreglos_pago;
    DROP TABLE IF EXISTS operaciones;
    DROP TABLE IF EXISTS clientes;
    DROP TABLE IF EXISTS estados_cliente;

    CREATE TABLE estados_cliente (
        estado_id        INTEGER PRIMARY KEY,
        estado           TEXT NOT NULL,
        subestado        TEXT NOT NULL,
        descripcion      TEXT
    );

    CREATE TABLE clientes (
        cliente_id       INTEGER PRIMARY KEY,
        documento        TEXT NOT NULL,
        nombre_completo  TEXT NOT NULL,
        sexo             TEXT,
        fecha_nacimiento DATE,
        email            TEXT,
        celular          TEXT,
        departamento     TEXT,
        fecha_ingreso    DATE,
        estado_id        INTEGER,
        FOREIGN KEY (estado_id) REFERENCES estados_cliente(estado_id)
    );

    CREATE TABLE operaciones (
        operacion_id     INTEGER PRIMARY KEY,
        cliente_id       INTEGER NOT NULL,
        fecha_otorgado   DATE NOT NULL,
        monto_otorgado   REAL NOT NULL,
        cantidad_cuotas  INTEGER NOT NULL,
        tasa_interes     REAL,
        canal            TEXT,
        anulada          INTEGER DEFAULT 0,
        sucursal_id      INTEGER,
        FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
    );

    CREATE TABLE cuotas (
        cuota_id         INTEGER PRIMARY KEY,
        operacion_id     INTEGER NOT NULL,
        numero_cuota     INTEGER NOT NULL,
        fecha_vencimiento DATE NOT NULL,
        fecha_cobro      DATE,
        monto            REAL NOT NULL,
        punitorios       REAL DEFAULT 0,
        anulada          INTEGER DEFAULT 0,
        FOREIGN KEY (operacion_id) REFERENCES operaciones(operacion_id)
    );

    CREATE TABLE gestiones (
        gestion_id       INTEGER PRIMARY KEY,
        cliente_id       INTEGER NOT NULL,
        fecha_gestion    DATE NOT NULL,
        canal            TEXT,
        resultado        TEXT,
        contactado       INTEGER,
        gestor           TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
    );

    CREATE TABLE arreglos_pago (
        arreglo_id       INTEGER PRIMARY KEY,
        cliente_id       INTEGER NOT NULL,
        fecha_alta       DATE NOT NULL,
        fecha_baja       DATE,
        deuda_total      REAL,
        cantidad_cuotas  INTEGER,
        monto_cuota      REAL,
        estado_arreglo   TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
    );
    """)
    con.commit()


def poblar_estados(con):
    estados = [
        (1, "Comercial",  "Al dia",              "Cliente al dia o atraso minimo"),
        (2, "Comercial",  "Atraso leve",         "Atraso menor a 30 dias"),
        (3, "Cobranzas",  "Negociacion",         "Mora gestionable 30-90 dias"),
        (4, "Cobranzas",  "Mora temprana",       "Atraso 90-180 dias"),
        (5, "Juridica",   "Mora tardia-Estudio", "Derivado a estudio externo"),
        (6, "Juridica",   "Incobrable",          "Deuda incobrable"),
    ]
    con.executemany("INSERT INTO estados_cliente VALUES (?,?,?,?)", estados)
    con.commit()


def rand_fecha(desde, hasta):
    delta = (hasta - desde).days
    return desde + timedelta(days=random.randint(0, max(delta, 1)))


def poblar(con):
    cur = con.cursor()
    deptos = ["Montevideo", "Canelones", "Maldonado", "Salto", "Paysandu",
              "Colonia", "Rivera", "Tacuarembo", "Soriano", "Florida"]
    canales = ["Digital", "Presencial", "Call Center"]
    canales_g = ["Llamada", "WhatsApp", "Email", "SMS"]
    resultados = ["Contactado-Promesa", "Contactado-Sin acuerdo", "No contesta",
                  "Numero equivocado", "Buzon de voz"]
    gestores = [fake.first_name() + " " + fake.last_name() for _ in range(15)]
    estados_arreglo = ["Vigente", "Cumplido", "Baja-Incumplimiento", "Baja-Refinanciado"]

    op_id = 1
    cuota_id = 1
    gestion_id = 1
    arreglo_id = 1

    for cid in range(1, N_CLIENTES + 1):
        # sesgo de estado: mayoria comercial, algunos en cobranza/juridica
        estado_id = random.choices([1, 2, 3, 4, 5, 6],
                                   weights=[35, 20, 20, 12, 8, 5])[0]
        sexo = random.choice(["M", "F"])
        f_nac = rand_fecha(datetime(1955, 1, 1), datetime(2003, 1, 1))
        f_ing = rand_fecha(FECHA_BASE, FECHA_HOY - timedelta(days=120))

        cur.execute("""INSERT INTO clientes
            (cliente_id, documento, nombre_completo, sexo, fecha_nacimiento,
             email, celular, departamento, fecha_ingreso, estado_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (cid, fake.unique.numerify("########"), fake.name(), sexo,
             f_nac.strftime("%Y-%m-%d"), fake.email(),
             "09" + fake.numerify("#######"),
             random.choice(deptos), f_ing.strftime("%Y-%m-%d"), estado_id))

        # 1-4 operaciones por cliente
        n_ops = random.randint(1, 4)
        for _ in range(n_ops):
            f_otorgado = rand_fecha(f_ing, FECHA_HOY - timedelta(days=30))
            monto = round(random.uniform(5000, 200000), 2)
            n_cuotas = random.choice([6, 12, 18, 24, 36])
            tasa = round(random.uniform(30, 90), 2)
            canal = random.choice(canales)
            anulada = 1 if random.random() < 0.05 else 0
            sucursal = random.choice([10, 20, 30, 40, 81])  # 81 = excluir

            cur.execute("""INSERT INTO operaciones
                (operacion_id, cliente_id, fecha_otorgado, monto_otorgado,
                 cantidad_cuotas, tasa_interes, canal, anulada, sucursal_id)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (op_id, cid, f_otorgado.strftime("%Y-%m-%d"), monto,
                 n_cuotas, tasa, canal, anulada, sucursal))

            # cuotas
            monto_cuota = round(monto * (1 + tasa/100) / n_cuotas, 2)
            for nc in range(1, n_cuotas + 1):
                f_vto = f_otorgado + timedelta(days=30 * nc)
                # probabilidad de pago segun estado del cliente
                prob_pago = {1: 0.97, 2: 0.90, 3: 0.70, 4: 0.50, 5: 0.25, 6: 0.10}[estado_id]
                pagada = random.random() < prob_pago and f_vto < FECHA_HOY
                if pagada:
                    # pago entre 0 y 20 dias despues del vto
                    f_cob = f_vto + timedelta(days=random.randint(-2, 20))
                    f_cob_str = f_cob.strftime("%Y-%m-%d") if f_cob < FECHA_HOY else None
                    punit = round(monto_cuota * random.uniform(0, 0.1), 2) if f_cob > f_vto else 0
                else:
                    f_cob_str = None
                    punit = 0

                cur.execute("""INSERT INTO cuotas
                    (cuota_id, operacion_id, numero_cuota, fecha_vencimiento,
                     fecha_cobro, monto, punitorios, anulada)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (cuota_id, op_id, nc, f_vto.strftime("%Y-%m-%d"),
                     f_cob_str, monto_cuota, punit, anulada))
                cuota_id += 1
            op_id += 1

        # gestiones (mas para clientes en cobranza/juridica)
        n_gest = {1: 1, 2: 2, 3: 6, 4: 10, 5: 8, 6: 3}[estado_id]
        for _ in range(n_gest):
            f_g = rand_fecha(f_ing, FECHA_HOY)
            res = random.choice(resultados)
            contactado = 1 if "Contactado" in res else 0
            cur.execute("""INSERT INTO gestiones
                (gestion_id, cliente_id, fecha_gestion, canal, resultado, contactado, gestor)
                VALUES (?,?,?,?,?,?,?)""",
                (gestion_id, cid, f_g.strftime("%Y-%m-%d"),
                 random.choice(canales_g), res, contactado, random.choice(gestores)))
            gestion_id += 1

        # arreglo de pago (solo algunos clientes en cobranza/juridica)
        if estado_id in (3, 4, 5) and random.random() < 0.4:
            f_alta = rand_fecha(f_ing, FECHA_HOY - timedelta(days=60))
            est_arr = random.choices(estados_arreglo, weights=[40, 25, 25, 10])[0]
            f_baja = None
            if est_arr.startswith("Baja"):
                f_baja = rand_fecha(f_alta, FECHA_HOY).strftime("%Y-%m-%d")
            deuda = round(random.uniform(10000, 150000), 2)
            kc = random.choice([3, 6, 12])
            cur.execute("""INSERT INTO arreglos_pago
                (arreglo_id, cliente_id, fecha_alta, fecha_baja, deuda_total,
                 cantidad_cuotas, monto_cuota, estado_arreglo)
                VALUES (?,?,?,?,?,?,?,?)""",
                (arreglo_id, cid, f_alta.strftime("%Y-%m-%d"), f_baja, deuda,
                 kc, round(deuda/kc, 2), est_arr))
            arreglo_id += 1

    con.commit()
    print(f"  clientes:     {N_CLIENTES}")
    print(f"  operaciones:  {op_id-1}")
    print(f"  cuotas:       {cuota_id-1}")
    print(f"  gestiones:    {gestion_id-1}")
    print(f"  arreglos:     {arreglo_id-1}")


def crear_indices(con):
    con.executescript("""
    CREATE INDEX idx_op_cliente   ON operaciones(cliente_id);
    CREATE INDEX idx_cuota_op     ON cuotas(operacion_id);
    CREATE INDEX idx_cuota_feccob ON cuotas(fecha_cobro);
    CREATE INDEX idx_gest_cliente ON gestiones(cliente_id);
    CREATE INDEX idx_arr_cliente  ON arreglos_pago(cliente_id);
    CREATE INDEX idx_cli_estado   ON clientes(estado_id);
    """)
    con.commit()


if __name__ == "__main__":
    print(f"Generando base sintetica '{DB_PATH}'...")
    con = sqlite3.connect(DB_PATH)
    crear_esquema(con)
    poblar_estados(con)
    poblar(con)
    crear_indices(con)
    con.close()
    print(f"Listo -> {DB_PATH}")
