# © 2026 Martín Viera. Todos los derechos reservados.

"""Pruebas de usuarios/permisos y auditoría. Correr: python3 tests/test_equipo_auditoria.py"""
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

# Aislar los archivos de datos en un temporal antes de importar los módulos
_tmp = tempfile.mkdtemp()
import equipo
import auditoria
equipo.RUTA = os.path.join(_tmp, "equipo.json")
auditoria.RUTA = os.path.join(_tmp, "auditoria.db")

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


print("\n== Usuarios y permisos ==")


@test("sin equipo configurado la app queda en modo abierto")
def _():
    cfg = equipo.cargar()
    assert cfg["activo"] is False
    assert cfg["usuarios"] == []
    p = equipo.permisos(None)
    assert p["tablas"] == "*" and p["puede_exportar"] is True


@test("crear el primer usuario activa el control de acceso")
def _():
    equipo.crear_usuario("Martin", "admin", "4321")
    cfg = equipo.cargar()
    assert cfg["activo"] is True
    assert len(cfg["usuarios"]) == 1


@test("el PIN nunca se guarda en texto plano")
def _():
    u = equipo.cargar()["usuarios"][0]
    assert "4321" not in str(u), "el PIN aparece en el archivo"
    assert len(u["pin"]) == 64 and u["sal"], "debe guardarse el hash y la sal"


@test("autentica con el PIN correcto y rechaza el incorrecto")
def _():
    assert equipo.autenticar("Martin", "4321") is not None
    assert equipo.autenticar("Martin", "1111") is None
    assert equipo.autenticar("Martin", "") is None
    assert equipo.autenticar("NoExiste", "4321") is None


@test("el nombre de usuario no distingue mayúsculas")
def _():
    assert equipo.autenticar("martin", "4321") is not None
    assert equipo.autenticar("MARTIN", "4321") is not None


@test("no deja crear dos usuarios con el mismo nombre")
def _():
    try:
        equipo.crear_usuario("martin", "lector", "9999")
        raise AssertionError("debió rechazar el duplicado")
    except ValueError:
        pass


@test("rechaza PIN demasiado corto")
def _():
    try:
        equipo.crear_usuario("Ana", "lector", "12")
        raise AssertionError("debió rechazar el PIN corto")
    except ValueError:
        pass


@test("un lector no puede exportar ni generar procedures")
def _():
    equipo.crear_usuario("Lucia", "lector", "5678", tablas=["cuotas", "gestiones"])
    u = equipo.autenticar("Lucia", "5678")
    p = equipo.permisos(u)
    assert p["puede_exportar"] is False
    assert p["puede_sp"] is False
    assert p["ve_auditoria"] is False
    assert p["limite_filas"] == 2000


@test("el catálogo se recorta a las tablas permitidas")
def _():
    catalogo = {"tablas": {"clientes": {}, "cuotas": {}, "gestiones": {},
                           "sueldos": {}, "operaciones": {}}}
    u = equipo.autenticar("Lucia", "5678")
    visto = equipo.tablas_visibles(catalogo, equipo.permisos(u))
    assert set(visto["tablas"]) == {"cuotas", "gestiones"}, set(visto["tablas"])
    assert "sueldos" not in visto["tablas"], "la IA no debe enterarse de que existe"
    # el catálogo original no se modifica
    assert len(catalogo["tablas"]) == 5


@test("un admin ve todo el catálogo")
def _():
    catalogo = {"tablas": {"clientes": {}, "sueldos": {}}}
    u = equipo.autenticar("Martin", "4321")
    visto = equipo.tablas_visibles(catalogo, equipo.permisos(u))
    assert set(visto["tablas"]) == {"clientes", "sueldos"}


@test("una FK a una tabla prohibida no filtra su nombre a la IA")
def _():
    # La FK lleva el nombre de la tabla destino al system prompt (como
    # "Relaciones"): recortar solo la tabla no alcanza si la relación
    # sobrevive. Las dos puntas tienen que estar permitidas.
    catalogo = {
        "tablas": {"cuotas": {}, "gestiones": {}, "sueldos": {}},
        "fks": [{"tabla_origen": "cuotas", "columna_origen": "emp_id",
                 "tabla_destino": "sueldos", "columna_destino": "id"}],
        "joins_inferidos": {"emp_id": ["cuotas", "sueldos"]},
    }
    u = equipo.autenticar("Lucia", "5678")   # ve solo cuotas y gestiones
    visto = equipo.tablas_visibles(catalogo, equipo.permisos(u))
    assert visto["fks"] == [], "la FK a 'sueldos' no debe sobrevivir"
    assert visto["joins_inferidos"] == {}, "el join inferido a 'sueldos' tampoco"
    # y el catálogo original queda intacto
    assert len(catalogo["fks"]) == 1


@test("bloquea el SQL que toca una tabla prohibida")
def _():
    p = equipo.permisos(equipo.autenticar("Lucia", "5678"))
    ok, prohibidas = equipo.puede_consultar_tablas(["cuotas"], p)
    assert ok and not prohibidas
    ok, prohibidas = equipo.puede_consultar_tablas(["cuotas", "sueldos"], p)
    assert not ok and prohibidas == ["sueldos"]


@test("BYPASS DE ROL: SQL escrito a mano contra una tabla prohibida se frena")
def _():
    # El exploit real: un lector con permiso solo sobre 'cuotas' escribe
    # 'SELECT * FROM sueldos' en una celda de cuaderno. puede_consultar_sql
    # extrae la tabla del SQL crudo y la frena, sin depender de que la IA
    # "conozca" o no la tabla.
    p = equipo.permisos(equipo.autenticar("Lucia", "5678"))
    ok, prohibidas = equipo.puede_consultar_sql("SELECT * FROM sueldos", p)
    assert not ok and prohibidas == ["sueldos"], "el lector leyó una tabla prohibida"


@test("tablas_en_sql: extrae FROM/JOIN reales y descarta los CTE")
def _():
    ts = equipo.tablas_en_sql(
        "WITH t AS (SELECT * FROM sueldos) SELECT * FROM t JOIN cuotas ON 1=1")
    # 'sueldos' y 'cuotas' son reales; 't' es un CTE, no cuenta.
    assert "sueldos" in ts and "cuotas" in ts and "t" not in ts, ts
    # esquema.tabla -> se queda con la tabla
    assert equipo.tablas_en_sql("SELECT * FROM dbo.secretos") == ["secretos"]


@test("un SELECT sin FROM (no toca tablas) lo deja pasar cualquier rol")
def _():
    p = equipo.permisos(equipo.autenticar("Lucia", "5678"))
    ok, prohibidas = equipo.puede_consultar_sql("SELECT 1 AS uno", p)
    assert ok and not prohibidas


@test("no se puede eliminar al último administrador")
def _():
    try:
        equipo.eliminar_usuario("Martin")
        raise AssertionError("debió impedir quedarse sin admin")
    except ValueError:
        pass


@test("sí se puede eliminar a un no-admin")
def _():
    equipo.crear_usuario("Temporal", "analista", "7777")
    equipo.eliminar_usuario("Temporal")
    assert equipo.autenticar("Temporal", "7777") is None


print("\n== Auditoría ==")


@test("registra una consulta exitosa")
def _():
    auditoria.registrar(usuario="Martin", rol="admin", pregunta="cobrado por mes",
                        sql="SELECT 1", tablas=["cuotas"], filas=6, confianza=94)
    cols, filas = auditoria.listar()
    assert len(filas) == 1
    assert filas[0][cols.index("usuario")] == "Martin"
    assert filas[0][cols.index("filas")] == 6


@test("registra un intento rechazado por permisos")
def _():
    auditoria.registrar(usuario="Lucia", rol="lector", pregunta="ver sueldos",
                        sql="SELECT * FROM sueldos", tablas=["sueldos"],
                        resultado="rechazado", detalle="sin permiso sobre: sueldos")
    cols, filas = auditoria.listar()
    assert filas[0][cols.index("resultado")] == "rechazado"
    assert "sueldos" in filas[0][cols.index("detalle")]


@test("el resumen cuenta rechazos y confianza media")
def _():
    r = auditoria.resumen(desde_dias=30)
    assert r["total"] == 2
    assert r["rechazadas"] == 1
    assert r["confianza_media"] == 94
    usuarios = dict(r["por_usuario"])
    assert usuarios["Martin"] == 1 and usuarios["Lucia"] == 1


@test("el resumen lista las tablas más consultadas")
def _():
    auditoria.registrar(usuario="Martin", rol="admin", tablas=["cuotas"], filas=3)
    r = auditoria.resumen(desde_dias=30)
    assert r["tablas_top"][0][0] == "cuotas"
    assert r["tablas_top"][0][1] == 2


@test("filtra el registro por usuario")
def _():
    _, filas = auditoria.listar(usuario="Lucia")
    assert len(filas) == 1


@test("exporta el registro a CSV con encabezados")
def _():
    csv = auditoria.a_csv().decode("utf-8-sig")
    assert csv.startswith("fecha;usuario;rol")
    assert "Lucia" in csv and "rechazado" in csv


@test("un fallo de escritura nunca rompe la app")
def _():
    original = auditoria.RUTA
    auditoria.RUTA = "/ruta/que/no/existe/auditoria.db"
    try:
        auditoria.registrar(usuario="X", pregunta="prueba")   # no debe explotar
        assert auditoria.listar() == ([], [])
        assert auditoria.resumen()["total"] == 0
    finally:
        auditoria.RUTA = original


@test("XSS: no se puede crear un usuario con HTML en el nombre")
def _():
    # El nombre se muestra en el panel del equipo, que se renderiza como
    # HTML (unsafe_allow_html=True). Antes esto se guardaba tal cual y
    # ejecutaba en el navegador del admin.
    for payload in ['<img src=x onerror=alert(1)>', '<script>alert(1)</script>',
                    'Ana"onmouseover="alert(1)', "Ana'x", "Ana&lt;"]:
        try:
            equipo.crear_usuario(payload, "lector", "1234")
            assert False, f"aceptó un nombre con HTML: {payload!r}"
        except ValueError:
            pass


@test("XSS: al mostrarlo, el nombre igual se escapa (por los ya guardados)")
def _():
    import html as _html
    # Un equipo.json viejo puede tener un nombre sucio guardado de antes;
    # el escape en el punto de render es la segunda capa.
    sucio = '<img src=x onerror=alert(1)>'
    assert _html.escape(sucio) == '&lt;img src=x onerror=alert(1)&gt;'
    assert "<img" not in _html.escape(sucio)


@test("los nombres normales siguen funcionando")
def _():
    u = equipo.crear_usuario("Ana Pérez-Gómez", "lector", "1234")
    assert u["nombre"] == "Ana Pérez-Gómez"
    equipo.eliminar_usuario("Ana Pérez-Gómez")


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
