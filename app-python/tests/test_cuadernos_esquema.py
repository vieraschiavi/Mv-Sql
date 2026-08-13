# © 2026 Martín Viera. Todos los derechos reservados.

"""Pruebas de cuadernos con variables, diagrama de relaciones y plan de ejecución."""
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

import cuadernos
import esquema_visual as ev
cuadernos.ARCHIVO = os.path.join(tempfile.mkdtemp(), "cuadernos.json")

pasadas = falladas = 0


def test(nombre):
    def deco(fn):
        global pasadas, falladas
        try:
            fn(); print(f"  ✓ {nombre}"); pasadas += 1
        except Exception as e:
            print(f"  ✗ {nombre}\n      {type(e).__name__}: {e}"); falladas += 1
    return deco


print("\n== Cuadernos y variables ==")


@test("detecta las variables de un texto, sin repetir y en orden")
def _():
    v = cuadernos.variables_usadas("cobrado de {{mes}} en {{sucursal}}, mes {{mes}}")
    assert v == ["mes", "sucursal"], v


@test("acepta espacios dentro de las llaves")
def _():
    assert cuadernos.variables_usadas("{{ mes }}") == ["mes"]


@test("ignora llaves que no son variables válidas")
def _():
    assert cuadernos.variables_usadas("{{123}} {{con espacio}} {}") == []


@test("sustituye variables en texto y deja intactas las que no tienen valor")
def _():
    t = cuadernos.sustituir_texto("Informe de {{mes}} en {{sucursal}}", {"mes": "enero"})
    assert t == "Informe de enero en {{sucursal}}", t


@test("EL SQL SE PARAMETRIZA: el valor nunca se pega en la consulta")
def _():
    sql, params = cuadernos.preparar_sql(
        "SELECT * FROM cuotas WHERE mes = {{mes}} AND suc = {{suc}}",
        {"mes": "2026-01", "suc": "Centro"})
    assert sql == "SELECT * FROM cuotas WHERE mes = ? AND suc = ?", sql
    assert params == ["2026-01", "Centro"], params


@test("una variable con intento de inyección viaja como dato, no como SQL")
def _():
    ataque = "2026-01'; DROP TABLE cuotas; --"
    sql, params = cuadernos.preparar_sql(
        "SELECT * FROM cuotas WHERE mes = {{mes}}", {"mes": ataque})
    assert "DROP" not in sql, "el ataque no puede aparecer en el SQL"
    assert sql.count("?") == 1 and params == [ataque]


@test("soporta el marcador de parámetros de otros motores")
def _():
    sql, _ = cuadernos.preparar_sql("WHERE a = {{x}}", {"x": 1}, marcador="%s")
    assert sql == "WHERE a = %s"


@test("guarda y recupera un cuaderno")
def _():
    celdas = [cuadernos.nueva_celda("markdown", "# Informe de {{mes}}"),
              cuadernos.nueva_celda("pregunta", "¿cuánto cobramos en {{mes}}?"),
              cuadernos.nueva_celda("sql", "SELECT * FROM cuotas WHERE mes = {{mes}}")]
    cuadernos.guardar("Cierre mensual", celdas, descripcion="Informe de cobranzas",
                      valores={"mes": "2026-01"})
    c = cuadernos.obtener("cierre mensual")
    assert c is not None and len(c["celdas"]) == 3
    assert c["valores"]["mes"] == "2026-01"


@test("reúne las variables de todas las celdas del cuaderno")
def _():
    c = cuadernos.obtener("Cierre mensual")
    assert cuadernos.variables_del_cuaderno(c) == ["mes"]


@test("avisa qué variables quedaron sin valor")
def _():
    c = cuadernos.obtener("Cierre mensual")
    c["celdas"].append(cuadernos.nueva_celda("sql", "WHERE suc = {{sucursal}}"))
    assert cuadernos.faltan_variables(c, {"mes": "2026-01"}) == ["sucursal"]
    assert cuadernos.faltan_variables(c, {"mes": "1", "sucursal": "Centro"}) == []


@test("guardar con el mismo nombre reemplaza, no duplica")
def _():
    cuadernos.guardar("Cierre mensual", [cuadernos.nueva_celda("markdown", "v2")])
    assert len(cuadernos.listar()) == 1
    assert cuadernos.obtener("Cierre mensual")["celdas"][0]["contenido"] == "v2"


@test("rechaza un tipo de celda inválido")
def _():
    try:
        cuadernos.guardar("Malo", [{"tipo": "video", "contenido": "x"}])
        raise AssertionError("debió rechazarlo")
    except ValueError:
        pass


@test("rechaza cuaderno sin nombre")
def _():
    try:
        cuadernos.guardar("  ", [])
        raise AssertionError("debió rechazarlo")
    except ValueError:
        pass


@test("mueve celdas de orden")
def _():
    c = {"celdas": [{"tipo": "markdown", "contenido": "A"},
                    {"tipo": "markdown", "contenido": "B"}]}
    cuadernos.mover_celda(c, 0, 1)
    assert [x["contenido"] for x in c["celdas"]] == ["B", "A"]
    cuadernos.mover_celda(c, 0, -1)   # fuera de rango: no rompe
    assert [x["contenido"] for x in c["celdas"]] == ["B", "A"]


@test("exporta el cuaderno a Markdown con las variables aplicadas")
def _():
    c = {"nombre": "Cierre", "descripcion": "Mes {{mes}}",
         "celdas": [{"tipo": "markdown", "contenido": "## Cobranzas de {{mes}}"},
                    {"tipo": "sql", "contenido": "SELECT 1"}]}
    md = cuadernos.a_markdown(c, {"mes": "enero"})
    assert "# Cierre" in md and "Cobranzas de enero" in md
    assert "```sql" in md and "{{mes}}" not in md


@test("elimina un cuaderno")
def _():
    cuadernos.eliminar("Cierre mensual")
    assert cuadernos.obtener("Cierre mensual") is None


print("\n== Diagrama de relaciones ==")

col = lambda n, pk=0: {"columna": n, "tipo": "INTEGER" if pk else "TEXT", "pk": pk, "nullable": 1}
CAT = {
    "tablas": {
        "clientes":    {"columnas": [col("cliente_id", 1), col("nombre")], "n_filas": 100},
        "operaciones": {"columnas": [col("operacion_id", 1), col("cliente_id")], "n_filas": 500},
        "feriados":    {"columnas": [col("fecha")], "n_filas": 20},
    },
    "fks": [{"tabla": "operaciones", "columna": "cliente_id",
             "tabla_destino": "clientes", "columna_destino": "cliente_id"}],
}


@test("genera un diagrama Mermaid válido")
def _():
    d = ev.diagrama_mermaid(CAT)
    assert d.startswith("erDiagram")
    assert "clientes {" in d and "operaciones {" in d
    assert "clientes ||--o{ operaciones" in d, d


@test("marca las claves primarias")
def _():
    assert "cliente_id PK" in ev.diagrama_mermaid(CAT)


@test("limita las columnas para que el diagrama no explote")
def _():
    cat = {"tablas": {"ancha": {"columnas": [col(f"c{i}") for i in range(30)]}}, "fks": []}
    d = ev.diagrama_mermaid(cat, max_columnas=5)
    assert "mas_25_columnas" in d, d


@test("nombres con espacios o símbolos no rompen el diagrama")
def _():
    cat = {"tablas": {"mi tabla-rara": {"columnas": [col("un campo")]}}, "fks": []}
    d = ev.diagrama_mermaid(cat)
    assert "mi_tabla_rara" in d and "un_campo" in d


@test("filtra el diagrama a las tablas elegidas")
def _():
    d = ev.diagrama_mermaid(CAT, tablas=["clientes"])
    assert "clientes {" in d and "operaciones {" not in d


@test("catálogo vacío devuelve diagrama vacío, no error")
def _():
    assert ev.diagrama_mermaid({"tablas": {}, "fks": []}) == ""


@test("lista las relaciones en texto")
def _():
    r = ev.resumen_relaciones(CAT)
    assert r == [("operaciones", "cliente_id", "clientes", "cliente_id")]


@test("detecta tablas sueltas, sin ninguna relación")
def _():
    assert ev.tablas_sin_relacion(CAT) == ["feriados"]


print("\n== Plan de ejecución ==")


@test("interpreta un escaneo completo y explica qué hacer")
def _():
    import sqlite3
    class Cx:
        dialecto = "sqlite"
        conn = sqlite3.connect(":memory:")
    Cx.conn.execute("CREATE TABLE t (a INTEGER, b TEXT)")
    Cx.conn.executemany("INSERT INTO t VALUES (?,?)", [(i, f"x{i}") for i in range(50)])
    filas, hallazgos = ev.plan_de_ejecucion(Cx, "SELECT * FROM t WHERE b = 'x1'")
    assert filas, "debe devolver el plan"
    assert any("escaneo" in h["titulo"] for h in hallazgos), hallazgos
    assert all(h["que_hacer"] for h in hallazgos), "cada hallazgo debe decir qué hacer"


@test("clasifica el costo de la consulta")
def _():
    assert ev.costo_estimado([]) == "desconocido"
    assert ev.costo_estimado([("SCAN t",)]) == "medio"
    assert ev.costo_estimado([("SCAN a",), ("SCAN b",), ("SCAN c",)]) == "pesado"
    assert ev.costo_estimado([("SEARCH t USING INDEX",)]) == "liviano"


@test("un motor sin EXPLAIN soportado no rompe nada")
def _():
    class Cx:
        motor = "sqlserver"
        dialecto = "SQL Server (T-SQL)"
        conn = None
    assert ev.plan_de_ejecucion(Cx, "SELECT 1") == ([], [])


@test("PostgreSQL SÍ tiene plan (el lookup por motor, no por dialecto)")
def _():
    # El bug: se buscaba por dialecto.lower() = 'postgresql' contra la clave
    # 'postgres', así que Postgres nunca encontraba su plantilla y el cliente
    # veía "no disponible". Ahora la clave es el motor.
    assert ev.SQL_EXPLAIN.get("postgres"), "postgres debe tener plantilla"
    # y aunque venga solo el dialecto real, el fallback lo infiere
    class Cx:
        dialecto = "PostgreSQL"
    motor = "postgres" if not getattr(Cx, "motor", "") else Cx.motor
    d = Cx.dialecto.lower()
    inferido = ("sqlserver" if "server" in d else "postgres" if "postgre" in d
                else "mysql" if "mysql" in d else "sqlite" if "sqlite" in d else "")
    assert inferido == "postgres", f"el fallback debía inferir postgres, dio {inferido}"


@test("SQL vacío o inválido no rompe nada")
def _():
    import sqlite3
    class Cx:
        dialecto = "sqlite"
        conn = sqlite3.connect(":memory:")
    assert ev.plan_de_ejecucion(Cx, "") == ([], [])
    assert ev.plan_de_ejecucion(Cx, "esto no es sql") == ([], [])


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
