"""Pruebas de la barrera de solo-lectura. Correr: python3 tests/test_solo_lectura.py

La regla "MV SQL NLP nunca modifica tu base" vivía solo en motor.py, el
orquestador. Cualquier camino que no pasara por ahí (una celda SQL de un
cuaderno, por ejemplo) llegaba al cursor sin ningún control. Estas
pruebas fijan la barrera en conectores.py, que es por donde pasan todos
los caminos.
"""
import os
import sqlite3
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

import conectores
from conectores import ConexionBD, SQLNoPermitido, asegurar_solo_lectura

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


def rechaza(sql):
    """True si la barrera bloquea ese SQL."""
    try:
        asegurar_solo_lectura(sql)
        return False
    except SQLNoPermitido:
        return True


# Base de prueba real, con datos, para probar contra un cursor de verdad
_tmp = tempfile.mkdtemp()
_DB = os.path.join(_tmp, "prueba.db")
_c = sqlite3.connect(_DB)
_c.execute("CREATE TABLE clientes (id INTEGER, nombre TEXT)")
_c.execute("INSERT INTO clientes VALUES (1, 'Ana'), (2, 'Bruno')")
_c.commit()
_c.close()


print("\n== Lo que SÍ tiene que dejar pasar (consultas legítimas) ==")


@test("un SELECT común")
def _():
    assert asegurar_solo_lectura("SELECT id, nombre FROM clientes") is True


@test("un CTE con WITH")
def _():
    assert asegurar_solo_lectura(
        "WITH t AS (SELECT id FROM clientes) SELECT * FROM t") is True


@test("REPLACE() como función de texto no es 'REPLACE INTO'")
def _():
    # Falso positivo clásico: bloquear la palabra 'replace' a secas rompe
    # una función de string perfectamente válida y de uso corriente.
    assert asegurar_solo_lectura(
        "SELECT REPLACE(nombre, 'a', 'A') FROM clientes") is True


@test("una columna que se llama 'update_at' no dispara la alarma")
def _():
    assert asegurar_solo_lectura("SELECT update_at FROM clientes") is True


@test("OFFSET no se confunde con SET")
def _():
    assert asegurar_solo_lectura(
        "SELECT id FROM clientes LIMIT 10 OFFSET 5") is True


@test("un ';' final suelto no molesta")
def _():
    assert asegurar_solo_lectura("SELECT id FROM clientes;") is True


print("\n== Lo que tiene que frenar ==")


@test("DELETE directo")
def _():
    assert rechaza("DELETE FROM clientes")


@test("DELETE con salto de línea (evadía la lista vieja de motor.py)")
def _():
    # motor.py buscaba el substring "delete " (con espacio): "DELETE\nFROM"
    # no matcheaba y pasaba de largo.
    assert rechaza("DELETE\nFROM clientes")


@test("DELETE con tabulación")
def _():
    assert rechaza("DELETE\tFROM clientes")


@test("DELETE escondido detrás de un comentario de bloque")
def _():
    assert rechaza("DELETE/**/FROM clientes")


@test("statements encadenados con ;")
def _():
    assert rechaza("SELECT 1; DROP TABLE clientes")


@test("CTE modificador (pasa el prefijo WITH y el chequeo de statement único)")
def _():
    assert rechaza(
        "WITH x AS (DELETE FROM clientes RETURNING id) SELECT * FROM x")


@test("UPDATE, DROP, ALTER, TRUNCATE, INSERT, CREATE, GRANT")
def _():
    for s in ["UPDATE clientes SET nombre='x'", "DROP TABLE clientes",
              "ALTER TABLE clientes ADD c INT", "TRUNCATE TABLE clientes",
              "INSERT INTO clientes VALUES (3,'z')", "CREATE TABLE t (a INT)",
              "GRANT ALL ON clientes TO x"]:
        assert rechaza(s), f"debería frenar: {s}"


@test("REPLACE INTO sí se frena (la forma peligrosa)")
def _():
    assert rechaza("REPLACE INTO clientes VALUES (1,'x')")


@test("PRAGMA y ATTACH")
def _():
    assert rechaza("PRAGMA table_info(clientes)")
    assert rechaza("ATTACH DATABASE '/tmp/otra.db' AS otra")


@test("consulta vacía")
def _():
    assert rechaza("") and rechaza("   ")


print("\n== Contra una conexión de verdad (no solo la función suelta) ==")


@test("ejecutar() devuelve datos con un SELECT")
def _():
    cx = ConexionBD("sqlite", ruta=_DB).conectar()
    cols, filas, _ = cx.ejecutar("SELECT id, nombre FROM clientes")
    assert cols == ["id", "nombre"], cols
    assert len(filas) == 2, filas


@test("INYECCIÓN DIRECTA: ejecutar('DROP TABLE clientes') no borra la tabla")
def _():
    # El caso que importa: saltearse motor.py por completo y llamar al
    # método público del conector, que es lo que hace cualquier código que
    # no pase por el orquestador (celdas SQL de cuadernos, por ejemplo).
    cx = ConexionBD("sqlite", ruta=_DB).conectar()
    try:
        cx.ejecutar("DROP TABLE clientes")
        assert False, "ejecutó un DROP: la barrera no está en el punto de ejecución"
    except SQLNoPermitido:
        pass

    # La tabla tiene que seguir existiendo Y con sus filas intactas.
    cols, filas, _ = cx.ejecutar("SELECT id, nombre FROM clientes")
    assert len(filas) == 2, f"la tabla quedó alterada: {filas}"

    # Y desde una conexión nueva, para descartar que sea caché de esta.
    otra = sqlite3.connect(_DB)
    n = otra.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='clientes'"
    ).fetchone()[0]
    otra.close()
    assert n == 1, "la tabla clientes desapareció de la base"


@test("ejecutar() frena el DELETE ANTES de llegar al cursor")
def _():
    cx = ConexionBD("sqlite", ruta=_DB).conectar()
    try:
        cx.ejecutar("DELETE FROM clientes")
        assert False, "tendría que haber lanzado SQLNoPermitido"
    except SQLNoPermitido:
        pass
    # y los datos siguen ahí
    _, filas, _ = cx.ejecutar("SELECT id FROM clientes")
    assert len(filas) == 2, "se borraron filas"


@test("el propio SQLite abre en modo read-only (defensa en profundidad)")
def _():
    # Aunque alguien saltee asegurar_solo_lectura() y vaya al cursor
    # directo, la conexión no puede escribir.
    cx = ConexionBD("sqlite", ruta=_DB).conectar()
    try:
        cx._con.execute("DELETE FROM clientes")
        assert False, "la conexión permitió escribir"
    except sqlite3.OperationalError as e:
        assert "readonly" in str(e).lower(), str(e)


@test("una ruta inexistente da un error accionable, no una base vacía")
def _():
    try:
        ConexionBD("sqlite", ruta=os.path.join(_tmp, "no_existe.db")).conectar()
        assert False, "tendría que haber fallado"
    except FileNotFoundError as e:
        assert "generar_db_demo" in str(e), "el mensaje debe decir qué hacer"


@test("las variables de cuaderno siguen viajando como parámetros")
def _():
    cx = ConexionBD("sqlite", ruta=_DB).conectar()
    cols, filas, _ = cx.ejecutar(
        "SELECT nombre FROM clientes WHERE id = ?", params=[1])
    assert filas == [("Ana",)], filas


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
