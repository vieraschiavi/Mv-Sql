"""Verifica los .bat del instalador. Correr: python3 tests/test_instalador_bat.py

Los .bat solo se pueden EJECUTAR en Windows, pero sus modos de falla mas
caros son estaticos y se detectan en cualquier lado. Y son caros de verdad:
cuando uno de estos esta mal, cmd.exe no da un error util — cierra la
ventana al instante. El cliente ve el programa "abrir y cerrar" y escribe
"no funciona el instalador", que es exactamente el reporte con el que no se
puede hacer nada.

Lo que se chequea:

  1. Solo ASCII. Un acento o un guion largo en un comentario alcanza para
     que cmd.exe se cierre. Es facil de meter sin darse cuenta al escribir
     un comentario en castellano.
  2. Saltos de linea CRLF en todas las lineas. Un LF suelto puede partir un
     comando al medio.
  3. Ningun `::` adentro de un bloque ( ). Es un bug clasico de cmd.exe:
     tira "sintaxis incorrecta". Adentro de parentesis va `rem`.
  4. Parentesis balanceados.
  5. Todo `goto :label` apunta a un label que existe.
  6. Paridad de los textos ES/EN/PT: si una variable de mensaje existe en
     un idioma y no en otro, el cliente de ese idioma ve una linea vacia o
     el nombre crudo de la variable en medio de la instalacion.
"""
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)

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


BATS = [n for n in sorted(os.listdir(APP)) if n.lower().endswith(".bat")]


def crudo(nombre):
    with open(os.path.join(APP, nombre), "rb") as fh:
        return fh.read()


def lineas(nombre):
    return crudo(nombre).decode("ascii", "replace").replace("\r", "").split("\n")


print(f"\n== Instaladores .bat encontrados: {', '.join(BATS)} ==")


@test("hay al menos un .bat (si no, este test no esta probando nada)")
def _():
    assert BATS, "no se encontro ningun .bat en app-python/"


for _nombre in BATS:

    @test(f"{_nombre}: solo ASCII")
    def _(n=_nombre):
        datos = crudo(n)
        malos = [(i, b) for i, b in enumerate(datos) if b > 127]
        if malos:
            pos = malos[0][0]
            ctx = datos[max(0, pos - 45):pos + 15].decode("ascii", "replace")
            raise AssertionError(
                f"{len(malos)} byte(s) no-ASCII, el primero en la posicion {pos}: ...{ctx}... "
                "(cmd.exe cierra la ventana sin mensaje)")

    @test(f"{_nombre}: todas las lineas terminan en CRLF")
    def _(n=_nombre):
        texto = crudo(n).decode("ascii", "replace")
        sueltos = len(re.findall(r"(?<!\r)\n", texto))
        assert sueltos == 0, f"{sueltos} linea(s) con LF suelto en vez de CRLF"

    @test(f"{_nombre}: ningun '::' adentro de un bloque ( )")
    def _(n=_nombre):
        # Fuera de un bloque, un comentario '::' es puro texto para cmd.exe:
        # sus parentesis (si tiene, ej. "todavia) y se relanza (desde alla")
        # no cuentan para nada. Adentro de un bloque ( ) ya abierto, en
        # cambio, cmd.exe SI sigue buscando el ')' de cierre linea a linea
        # aunque la linea empiece con '::' -- por eso ahi es un bug real.
        prof, malos = 0, []
        for i, l in enumerate(lineas(n), 1):
            s = l.strip()
            es_comentario = s.startswith("::")
            if prof > 0 and es_comentario:
                malos.append(f"L{i}: {s[:55]}")
            if es_comentario and prof == 0:
                continue
            limpio = re.sub(r'"[^"]*"', "", re.sub(r"\^.", "", s))
            prof = max(0, prof + limpio.count("(") - limpio.count(")"))
        assert not malos, (
            "cmd.exe tira 'sintaxis incorrecta' con :: adentro de parentesis; "
            "usa 'rem'. " + "; ".join(malos))

    @test(f"{_nombre}: parentesis balanceados")
    def _(n=_nombre):
        prof = 0
        for l in lineas(n):
            s = l.strip()
            if s.startswith("::") and prof == 0:
                continue    # comentario a nivel superior: cmd.exe no lo mira
            s = re.sub(r'"[^"]*"', "", re.sub(r"\^.", "", s))
            prof = max(0, prof + s.count("(") - s.count(")"))
        assert prof == 0, f"quedan {prof} parentesis sin cerrar"

    @test(f"{_nombre}: todo goto apunta a un label que existe")
    def _(n=_nombre):
        ls = lineas(n)
        labels = {s.strip()[1:].split()[0].lower() for s in ls
                  if s.strip().startswith(":") and not s.strip().startswith("::")
                  and len(s.strip()) > 1}
        faltan = []
        for i, l in enumerate(ls, 1):
            for g in re.findall(r"goto\s+:?(\w+)", l, re.I):
                if g.lower() not in labels and g.lower() != "eof":
                    faltan.append(f"L{i}: goto :{g}")
        assert not faltan, "; ".join(faltan)


@test("INICIAR_MVSQL.bat: los textos ES/EN/PT tienen las mismas variables")
def _():
    ls = lineas("INICIAR_MVSQL.bat")
    bloques, actual = {}, None
    for l in ls:
        s = l.strip()
        m = re.match(r"^:textos_(es|en|pt)$", s)
        if m:
            actual = m.group(1)
            bloques[actual] = set()
            continue
        if actual and s.startswith("goto "):
            actual = None
            continue
        if actual:
            v = re.match(r'^set\s+"(M_[A-Z0-9_]+)=', s)
            if v:
                bloques[actual].add(v.group(1))

    assert set(bloques) == {"es", "en", "pt"}, f"bloques hallados: {sorted(bloques)}"
    base = bloques["es"]
    assert base, "el bloque ES no tiene ninguna variable M_*"
    for lang in ("en", "pt"):
        faltan = sorted(base - bloques[lang])
        sobran = sorted(bloques[lang] - base)
        assert not faltan, f"{lang.upper()} no define: {', '.join(faltan)}"
        assert not sobran, f"{lang.upper()} define de mas: {', '.join(sobran)}"
    print(f"      {len(base)} mensajes x 3 idiomas")


@test("INICIAR_MVSQL.bat: toda variable M_* que se usa esta definida")
def _():
    ls = lineas("INICIAR_MVSQL.bat")
    definidas = {m.group(1) for l in ls
                 for m in [re.match(r'^set\s+"(M_[A-Z0-9_]+)=', l.strip())] if m}
    usadas = set()
    for l in ls:
        if re.match(r'^\s*set\s+"M_', l):
            continue
        usadas |= set(re.findall(r"!(M_[A-Z0-9_]+)!", l))
    faltan = sorted(usadas - definidas)
    assert not faltan, f"se usan pero no se definen: {', '.join(faltan)}"


@test("INICIAR_MVSQL.bat: toda variable M_* que se define se usa")
def _():
    # El caso inverso del anterior: una variable de mensaje que se define y
    # nunca se muestra es casi siempre un resto de un diseno anterior (paso
    # por esto de verdad: M_DISCO_ACTUAL quedo asi al escribir este bloque).
    ls = lineas("INICIAR_MVSQL.bat")
    definidas = {m.group(1) for l in ls
                 for m in [re.match(r'^set\s+"(M_[A-Z0-9_]+)=', l.strip())] if m}
    usadas = set()
    for l in ls:
        if re.match(r'^\s*set\s+"M_', l):
            continue
        usadas |= set(re.findall(r"!(M_[A-Z0-9_]+)!", l))
    sobran = sorted(definidas - usadas)
    assert not sobran, f"se definen pero nunca se muestran: {', '.join(sobran)}"


@test("INICIAR_MVSQL.bat: instala requirements.txt y los extras por separado")
def _():
    texto = crudo("INICIAR_MVSQL.bat").decode("ascii")
    assert "-r requirements.txt" in texto, "no instala el nucleo"
    assert "-r requirements-extras.txt" in texto, "no instala los extras"
    assert texto.count("--no-cache-dir") >= 2, (
        "falta --no-cache-dir: pip guardaria una copia de cada wheel ademas "
        "de instalarla, casi duplicando el espacio necesario")


@test("el diagnostico de errores acierta la causa real (incluido el disco lleno)")
def _():
    # Los patrones se LEEN del .bat, no se copian aca: una lista duplicada se
    # despega en silencio el dia que alguien edita solo uno de los dos lados,
    # y este test seguiria en verde probando algo que ya no existe.
    orden = []
    for l in lineas("INICIAR_MVSQL.bat"):
        s = l.strip()
        if not s.startswith("findstr"):
            continue
        pats = re.findall(r'/c:"([^"]+)"', s)
        if pats:
            orden.append(pats)
    assert len(orden) >= 4, (
        f"se esperaban al menos 4 findstr de diagnostico, hay {len(orden)}: "
        "se saco alguna causa del .bat")

    def diagnostico(log):
        b = log.lower()
        for i, pats in enumerate(orden):
            if any(p.lower() in b for p in pats):
                return i
        return -1                              # ninguna causa reconocida

    DISCO, PERMISOS, PYVER, RED, NINGUNA = 0, 1, 2, 3, -1
    casos = [
        # El error exacto que reporto un cliente en Windows. Antes de esto,
        # el .bat contestaba "revisa tu conexion" a este mismo texto.
        ("ERROR: Could not install packages due to an OSError: "
         "[Errno 28] No space left on device", DISCO),
        ("OSError: [Errno 28] No space left on device", DISCO),
        ("ERROR: Could not install packages due to an OSError: "
         "[Errno 13] Permission denied", PERMISOS),
        ("ERROR: Could not install packages due to an OSError: "
         "[WinError 5] Access is denied", PERMISOS),
        ("ERROR: Could not find a version that satisfies the requirement shap>=0.45", PYVER),
        ("ERROR: Package 'streamlit' requires a different Python: 3.7.9 not in '>=3.9'", PYVER),
        ("WARNING: Retrying after connection broken by 'ProxyError'\n"
         "ERROR: Max retries exceeded", RED),
        ("urllib3.exceptions.SSLError: certificate verify failed", RED),
        ("ERROR: algo que nunca vimos antes", NINGUNA),
    ]
    for log, esperado in casos:
        got = diagnostico(log)
        assert got == esperado, (
            f"log {log.splitlines()[0][:60]!r} -> causa {got}, se esperaba {esperado}")


@test("los dos requirements existen y no se pisan")
def _():
    for f in ("requirements.txt", "requirements-extras.txt"):
        assert os.path.exists(os.path.join(APP, f)), f"falta {f}"

    def paquetes(f):
        out = set()
        with open(os.path.join(APP, f), encoding="utf-8") as fh:
            for l in fh:
                l = l.strip()
                if l and not l.startswith("#"):
                    out.add(re.split(r"[><=\[]", l)[0].strip().lower())
        return out

    nucleo, extras = paquetes("requirements.txt"), paquetes("requirements-extras.txt")
    assert nucleo, "el nucleo quedo vacio"
    assert extras, "los extras quedaron vacios"
    repes = nucleo & extras
    assert not repes, f"estan en los dos archivos: {', '.join(sorted(repes))}"
    # Lo pesado y opcional NO puede volver al nucleo sin que este test avise:
    # es justo lo que hacia fallar el install entero en un disco con poco lugar.
    for p in ("pyarrow", "shap", "faker"):
        assert p not in nucleo, (
            f"{p} volvio a requirements.txt; es opcional en el codigo "
            "(try/except con fallback) y pesa cientos de MB")


@test("los extras son de verdad opcionales en el codigo (try/except, no import directo)")
def _():
    for mod, archivo in (("shap", "app.py"), ("pyarrow", "app.py")):
        with open(os.path.join(APP, archivo), encoding="utf-8") as fh:
            texto = fh.read()
        # No puede haber un import de nivel de modulo: eso volaria la app entera.
        assert not re.search(rf"^import {mod}\b", texto, re.M), (
            f"{archivo} importa {mod} a nivel de modulo: si falta, no arranca nada")
        assert not re.search(rf"^from {mod}\b", texto, re.M), (
            f"{archivo} importa {mod} a nivel de modulo")
        assert mod in texto, f"{mod} ya no se usa en {archivo}: sacalo de los extras"


print(f"\n  {pasadas} pasadas · {falladas} falladas\n")
sys.exit(1 if falladas else 0)
