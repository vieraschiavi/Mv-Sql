# © 2026 Martín Viera. Todos los derechos reservados.

"""Pruebas del trial y la licencia paga. Correr: python3 tests/test_licencia.py

licencia.py es el módulo que hace cumplir "7 días de prueba gratis, después
hay que pagar" — es la promesa de negocio, no un detalle interno, así que
merece la misma cobertura que el resto (o más): que el trial dure
exactamente TRIAL_DIAS, que una licencia paga gane sobre el trial, que
adelantar el reloj no regale días, y que editar el archivo de marca a mano
reinicie el trial en vez de extenderlo (es la única defensa anti-manipulación
que este módulo puede dar sin un servidor propio — ver el docstring del
módulo).
"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

import licencia  # noqa: E402

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


def aislar():
    """Cada test corre contra su propio directorio: nada de estado compartido
    entre casos (a diferencia de equipo/auditoría, acá el estado — la fecha
    de inicio del trial — es justo lo que cada test necesita controlar)."""
    tmp = tempfile.mkdtemp()
    licencia.RUTA_MARCA_TRIAL = os.path.join(tmp, ".mvsql_trial.json")
    licencia.RUTA_LICENCIA = os.path.join(tmp, "licencia_mvsql.json")
    return tmp


def marca_con_inicio(hace_dias, firma_valida=True):
    """Fabrica un archivo de marca como si el trial hubiera arrancado
    `hace_dias` días atrás, con la misma firma que produciría el módulo."""
    inicio = (datetime.now(timezone.utc) - timedelta(days=hace_dias)).isoformat()
    firma = licencia._firma(inicio) if firma_valida else "firma-truchada"
    with open(licencia.RUTA_MARCA_TRIAL, "w", encoding="utf-8") as fh:
        json.dump({"inicio": inicio, "firma": firma}, fh)
    return inicio


def licencia_con_vencimiento(dias_desde_hoy):
    vence = (datetime.now(timezone.utc) + timedelta(days=dias_desde_hoy)).isoformat()
    with open(licencia.RUTA_LICENCIA, "w", encoding="utf-8") as fh:
        json.dump({"vence": vence, "plan": "profesional", "modo": "own_ai"}, fh)


print("\n== La promesa de negocio: 7 días, ni más ni menos ==")


@test("TRIAL_DIAS es 7 (si esto cambia solo, el trial cambió de duración sin querer)")
def _():
    assert licencia.TRIAL_DIAS == 7


print("\n== Primera vez que se abre la app ==")


@test("sin marca previa, crea una y da acceso con los 7 días completos")
def _():
    aislar()
    assert not os.path.exists(licencia.RUTA_MARCA_TRIAL)
    r = licencia.verificar_acceso()
    assert r == {"permitido": True, "dias_restantes": 7, "con_licencia": False}
    assert os.path.exists(licencia.RUTA_MARCA_TRIAL), "debe persistir la marca"


@test("la marca no se reinicia en llamadas siguientes (no regala más días)")
def _():
    aislar()
    primera = licencia.verificar_acceso()
    segunda = licencia.verificar_acceso()
    assert primera["dias_restantes"] == segunda["dias_restantes"] == 7
    with open(licencia.RUTA_MARCA_TRIAL, encoding="utf-8") as fh:
        marcas = json.load(fh)
    assert "inicio" in marcas and "firma" in marcas


print("\n== Durante y al final del trial ==")


@test("a mitad del trial, cuenta los días correctos")
def _():
    aislar()
    marca_con_inicio(hace_dias=3)
    r = licencia.verificar_acceso()
    assert r == {"permitido": True, "dias_restantes": 4, "con_licencia": False}


@test("el último día (día 6 de 7) todavía deja pasar")
def _():
    aislar()
    marca_con_inicio(hace_dias=6)
    r = licencia.verificar_acceso()
    assert r["permitido"] is True and r["dias_restantes"] == 1


@test("al día 7 exacto, se corta")
def _():
    aislar()
    marca_con_inicio(hace_dias=7)
    r = licencia.verificar_acceso()
    assert r == {"permitido": False, "dias_restantes": 0, "con_licencia": False}


@test("bien pasado el trial, se corta y no da un número negativo de días")
def _():
    aislar()
    marca_con_inicio(hace_dias=40)
    r = licencia.verificar_acceso()
    assert r["permitido"] is False
    assert r["dias_restantes"] == 0, "max(0, ...) tiene que ganar, nunca un negativo"


print("\n== Manipulación del reloj y del archivo (lo que sí se detecta) ==")


@test("reloj del sistema adelantado hacia atrás: no regala días, corta")
def _():
    aislar()
    # Marca "en el futuro" respecto al reloj actual = el usuario atrasó el
    # reloj después de instalar, o lo adelantó antes de la primera vez.
    marca_con_inicio(hace_dias=-5)
    r = licencia.verificar_acceso()
    assert r == {"permitido": False, "dias_restantes": 0, "con_licencia": False}


@test("editar la fecha a mano sin actualizar la firma reinicia el trial, no lo extiende")
def _():
    aislar()
    # Alguien cambia "inicio" para simular que el trial recién empezó, pero
    # no puede recalcular la firma (no tiene _SAL). Si esto "funcionara",
    # sería la forma más obvia de estirar el trial para siempre.
    marca_con_inicio(hace_dias=40, firma_valida=False)
    r = licencia.verificar_acceso()
    assert r["permitido"] is True and r["dias_restantes"] == 7, (
        "firma inválida debe descartar la marca vieja y arrancar un trial nuevo, "
        "no conservar los 40 días de manipulación"
    )
    # Y la marca en disco queda reemplazada por una con firma válida.
    with open(licencia.RUTA_MARCA_TRIAL, encoding="utf-8") as fh:
        nueva = json.load(fh)
    assert nueva["firma"] == licencia._firma(nueva["inicio"])


@test("archivo de marca corrupto (no es JSON) no rompe la app, reinicia el trial")
def _():
    aislar()
    with open(licencia.RUTA_MARCA_TRIAL, "w", encoding="utf-8") as fh:
        fh.write("esto no es json{{{")
    r = licencia.verificar_acceso()
    assert r["permitido"] is True and r["dias_restantes"] == 7


print("\n== Licencia paga ==")


@test("licencia vigente da acceso completo, sin días ni trial")
def _():
    aislar()
    licencia_con_vencimiento(dias_desde_hoy=30)
    r = licencia.verificar_acceso()
    assert r == {"permitido": True, "dias_restantes": None, "con_licencia": True}


@test("licencia vigente gana aunque el trial ya esté vencido")
def _():
    aislar()
    marca_con_inicio(hace_dias=40)  # trial hace rato vencido
    licencia_con_vencimiento(dias_desde_hoy=1)
    r = licencia.verificar_acceso()
    assert r["permitido"] is True and r["con_licencia"] is True


@test("licencia vencida no cuenta: cae al trial normal")
def _():
    aislar()
    licencia_con_vencimiento(dias_desde_hoy=-1)
    r = licencia.verificar_acceso()
    assert r["con_licencia"] is False
    assert r["permitido"] is True and r["dias_restantes"] == 7  # trial recién arranca


@test("licencia con JSON corrupto no rompe, cae al trial")
def _():
    aislar()
    with open(licencia.RUTA_LICENCIA, "w", encoding="utf-8") as fh:
        fh.write("{ no cierra")
    r = licencia.verificar_acceso()
    assert r["con_licencia"] is False and r["permitido"] is True


@test("licencia sin campo 'vence' no rompe, cae al trial")
def _():
    aislar()
    with open(licencia.RUTA_LICENCIA, "w", encoding="utf-8") as fh:
        json.dump({"plan": "profesional"}, fh)
    r = licencia.verificar_acceso()
    assert r["con_licencia"] is False and r["permitido"] is True


print("\n== Robustez de bajo nivel ==")


@test("sin permiso de escritura para la marca, sigue funcionando (solo no persiste)")
def _():
    tmp = aislar()
    # Directorio padre inexistente => open() para escribir tira OSError,
    # que _crear_marca_trial() debe atrapar sin voltear la app.
    licencia.RUTA_MARCA_TRIAL = os.path.join(tmp, "no-existe", ".mvsql_trial.json")
    r = licencia.verificar_acceso()
    assert r["permitido"] is True and r["dias_restantes"] == 7


@test("la firma depende del contenido: dos inicios distintos dan firmas distintas")
def _():
    a = licencia._firma("2026-01-01T00:00:00+00:00")
    b = licencia._firma("2026-01-02T00:00:00+00:00")
    assert a != b
    assert len(a) == 64  # sha256 hex


@test("el PIN/salt de licencia.py no depende de una clave externa (no hay .env que falte)")
def _():
    # Documentado en el módulo: _SAL no es secreta. Este test fija que
    # _firma() sea determinística y no dependa de una variable de entorno
    # que en una instalación limpia no está seteada.
    for var in ("MVSQL_LICENCIA_SECRETO", "MVSQL_SECRET_KEY"):
        os.environ.pop(var, None)
    assert licencia._firma("x") == hashlib.sha256((licencia._SAL + "x").encode()).hexdigest()


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
