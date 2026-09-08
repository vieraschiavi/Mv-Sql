# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_modo_servidor.py — el estado se queda donde lo pusieron
==================================================================
El modo servidor existe para un caso concreto: un consultor entra a
trabajar a un cliente y los datos del cliente NO pueden terminar en su
laptop. La app corre en un servidor del cliente, el consultor entra por
el navegador, y cuando el trabajo termina se borra el volumen y no queda
nada en ningún lado.

Toda esa promesa se apoya en una sola cosa: que con MVSQL_DATOS puesta,
la app escriba en esa carpeta Y EN NINGUNA OTRA. Si un módulo se olvida
de pasar por rutas.py y sigue escribiendo al lado del código, el
consultor se lleva a su casa las credenciales de la base del cliente sin
enterarse — y no hay error, no hay aviso, todo "funciona".

Por eso el test central de este archivo (`ni un archivo fuera del
volumen`) no mira rutas declaradas: EJERCITA los módulos que escriben y
después cuenta los archivos que aparecieron en cada lado.

El otro lado del contrato, igual de importante: SIN la variable no puede
cambiar nada. Un cliente que ya tiene el producto instalado tiene su
licencia y su equipo al lado del código; mover ese default le rompe la
instalación en la próxima actualización.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(RAIZ)
sys.path.insert(0, RAIZ)

import licencia  # noqa: E402
import rutas  # noqa: E402

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


def en_subproceso(codigo, datos=None):
    """Corre `codigo` en un Python nuevo, con MVSQL_DATOS puesta o no.

    Tiene que ser un proceso aparte y no un monkeypatch: las rutas se
    resuelven en el import de cada módulo (RUTA = rutas.en_datos(...)),
    así que reimportar en el mismo proceso devolvería lo cacheado en
    sys.modules y el test daría verde sin probar nada.
    """
    env = dict(os.environ)
    env.pop(rutas.VARIABLE, None)
    if datos is not None:
        env[rutas.VARIABLE] = datos
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"el subproceso falló:\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()


LEER_RUTAS = """
import equipo, auditoria, licencia, eula, guardadas, json
print(json.dumps({
    "equipo": equipo.RUTA,
    "auditoria": auditoria.RUTA,
    "licencia": licencia.RUTA_LICENCIA,
    "trial": licencia.RUTA_MARCA_TRIAL,
    "eula": eula.RUTA_MARCA_EULA,
    "guardadas": guardadas.ARCHIVO_DEFAULT,
}))
"""


print("\n== Sin la variable, NADA cambia (no se rompe lo ya instalado) ==")


@test("el default sigue siendo la carpeta del código")
def _():
    assert rutas.carpeta_datos() == RAIZ, rutas.carpeta_datos()


@test("los cinco módulos siguen escribiendo donde escribían siempre")
def _():
    r = json.loads(en_subproceso(LEER_RUTAS))
    for clave in ("equipo", "auditoria", "licencia", "trial", "eula"):
        assert os.path.dirname(r[clave]) == RAIZ, f"{clave} se movió a {r[clave]}"
    # guardadas es la excepción histórica: siempre vivió en ~/.mvsql y sin
    # la variable tiene que seguir ahí.
    assert r["guardadas"].startswith(os.path.expanduser("~")), r["guardadas"]


print("\n== Con MVSQL_DATOS, todo el estado se muda ==")


@test("carpeta_datos() devuelve la carpeta pedida y la crea si no existe")
def _():
    base = tempfile.mkdtemp()
    destino = os.path.join(base, "no", "existe", "todavia")
    try:
        os.environ[rutas.VARIABLE] = destino
        assert rutas.carpeta_datos() == destino
        assert os.path.isdir(destino), "no creó la carpeta"
    finally:
        os.environ.pop(rutas.VARIABLE, None)
        shutil.rmtree(base, ignore_errors=True)


@test("LOS SEIS archivos de estado caen en el volumen, ninguno al lado del código")
def _():
    vol = tempfile.mkdtemp()
    try:
        r = json.loads(en_subproceso(LEER_RUTAS, datos=vol))
        for clave, ruta in r.items():
            assert os.path.dirname(ruta) == vol, f"{clave} quedó en {ruta}, no en el volumen"
    finally:
        shutil.rmtree(vol, ignore_errors=True)


@test("una ruta imposible NO rompe la app: avisa y cae al default")
def _():
    # Un consultor en medio de una visita al cliente prefiere la app
    # andando en el default antes que un stack trace en la pantalla.
    try:
        os.environ[rutas.VARIABLE] = "/proc/no-se-puede-crear-aca/datos"
        assert rutas.carpeta_datos() == RAIZ
    finally:
        os.environ.pop(rutas.VARIABLE, None)


print("\n== La prueba de fuego: escribir de verdad y contar archivos ==")


@test("NI UN ARCHIVO FUERA DEL VOLUMEN al crear equipo, auditoría y licencia")
def _():
    vol = tempfile.mkdtemp()
    # Huella de la carpeta del código ANTES. Si al terminar aparece un
    # archivo nuevo acá, es exactamente el escenario que este modo
    # promete que no puede pasar.
    antes = set(os.listdir(RAIZ))
    try:
        salida = en_subproceso("""
import equipo, auditoria, eula, licencia, json, os
equipo.crear_usuario("Consultor", "admin", "9876")
auditoria.registrar(usuario="Consultor", rol="admin",
                    pregunta="cuanto facturamos", sql="SELECT 1",
                    filas=1, resultado="ok", detalle="")
eula.registrar_aceptacion()
print(json.dumps(sorted(os.listdir(os.environ["MVSQL_DATOS"]))))
""", datos=vol)
        creados = json.loads(salida)
        # Que haya escrito de verdad: un test que no escribe nada pasaría
        # esta prueba sin probar nada.
        assert "equipo.json" in creados, creados
        assert "auditoria.db" in creados, creados
        assert ".eula_aceptado" in creados, creados

        nuevos = set(os.listdir(RAIZ)) - antes
        assert not nuevos, f"se escribió FUERA del volumen: {sorted(nuevos)}"
    finally:
        shutil.rmtree(vol, ignore_errors=True)


print("\n== Propietario: ni escribe marca de trial ni pide licencia ==")


@test("preparar-propietario.py deja la app con acceso completo")
def _():
    vol = tempfile.mkdtemp()
    try:
        guion = os.path.join(REPO, "servidor", "preparar-propietario.py")
        assert os.path.exists(guion), "falta servidor/preparar-propietario.py"
        env = dict(os.environ, **{rutas.VARIABLE: vol})
        r = subprocess.run([sys.executable, guion], env=env,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

        estado = json.loads(en_subproceso("""
import licencia, json, os
acceso = licencia.verificar_acceso()
print(json.dumps({
    "permitido": acceso["permitido"],
    "con_licencia": acceso["con_licencia"],
    "plan": licencia.plan_licencia_vigente(),
    "avanzadas": licencia.funciones_avanzadas_habilitadas(),
    "escribio_trial": os.path.exists(licencia.RUTA_MARCA_TRIAL),
}))
""", datos=vol))
        assert estado["permitido"] and estado["con_licencia"], estado
        assert estado["plan"] == "propietario", estado
        assert estado["avanzadas"], "el propietario tiene que tener todo habilitado"
        # El punto de "sin escribir licencia": verificar_acceso() corta en
        # la primera línea cuando hay licencia vigente y NO crea la marca.
        assert not estado["escribio_trial"], "escribió la marca de trial igual"
    finally:
        shutil.rmtree(vol, ignore_errors=True)


@test("sin correr ese script, la misma carpeta arranca en trial (el script hace algo)")
def _():
    vol = tempfile.mkdtemp()
    try:
        estado = json.loads(en_subproceso("""
import licencia, json
acceso = licencia.verificar_acceso()
print(json.dumps({"con_licencia": acceso["con_licencia"],
                  "dias": acceso["dias_restantes"]}))
""", datos=vol))
        assert not estado["con_licencia"], "dio licencia sin que nadie la escribiera"
        assert estado["dias"] == licencia.TRIAL_DIAS, estado
    finally:
        shutil.rmtree(vol, ignore_errors=True)


print(f"\n  {_pasadas} pasadas · {_falladas} falladas\n")
sys.exit(1 if _falladas else 0)
