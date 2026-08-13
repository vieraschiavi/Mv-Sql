# © 2026 Martín Viera. Todos los derechos reservados.

"""
test_arranque_app.py — que app.py ARRANQUE, no solo que exista
==================================================================
Este archivo nace de un bug que estuvo publicado: al sacar los emojis de
la interfaz, la etiqueta del selector de idioma pasó de "🌐" a
t["idioma"], y `t` recién se asigna cuatro líneas más abajo. Resultado:

    NameError: name 't' is not defined   (app.py, sidebar)

La app Python entera moría con un traceback apenas el cliente aceptaba el
EULA. Todo lo demás estaba en verde: los 18 tests del .bat, el zip, los
instaladores NSIS, la barrera de solo-lectura. Nada de eso ejecuta app.py,
así que nada lo vio.

Se cubre de dos formas, a propósito:

1. Un chequeo ESTÁTICO de nombres usados antes de asignarse a nivel de
   módulo. No necesita ninguna dependencia instalada, así que corre en
   cualquier máquina y en CI, que es donde tiene que fallar. Cubre la
   clase entera de bug, no solo esta variable.

2. Un arranque REAL con el framework de test de Streamlit, que ejecuta el
   script y devuelve las excepciones. Solo corre si streamlit está
   instalado; si no, se saltea. Es el único que prueba que la app
   realmente levanta, pero no se puede exigir porque la suite de este
   proyecto está hecha para correr sin pip install (ver requirements.txt).
"""
import ast
import builtins
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

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


def nombres_usados_antes_de_definirse(ruta):
    """
    Devuelve [(nombre, linea_uso, linea_definicion)] de los nombres que a
    NIVEL DE MÓDULO se usan antes de tener valor.

    El recorrido respeta el alcance, que es todo el problema de este
    chequeo. Un primer intento con ast.walk() sobre cada statement marcó
    decenas de falsos positivos, porque desciende adentro de las funciones
    (donde `p` o `v` son locales, y `def f(conf, t)` hace que `t` parezca
    global) y trata un `if` de treinta líneas como un solo punto en el
    tiempo, con lo que un nombre asignado en su línea 2 y usado en su
    línea 15 salía marcado.

    Reglas, entonces:
      - El cuerpo de def/class NO se mira: ahí un global se resuelve
        cuando la función se llama, no donde está escrita. Sí se miran sus
        decoradores y los valores por defecto, que se evalúan al definirla.
      - Los statements compuestos (if/for/while/with/try) se recorren por
        adentro y EN ORDEN, no de golpe.
      - Los alcances propios de lambda y de las comprensiones se saltean:
        sus variables no existen afuera.
    """
    arbol = ast.parse(open(ruta, encoding="utf-8").read(), filename=ruta)
    definidos = {}
    problemas = []
    conocidos = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__spec__"}

    def registrar(nodo):
        """Marca como definidos los nombres que este destino asigna."""
        if nodo is None:
            return
        for n in ast.walk(nodo):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                definidos.setdefault(n.id, n.lineno)

    def usar(expr):
        """Anota los nombres que esta expresión LEE, sin entrar en alcances propios."""
        if expr is None:
            return
        pila = [expr]
        while pila:
            n = pila.pop()
            if isinstance(n, (ast.Lambda, ast.ListComp, ast.SetComp,
                              ast.DictComp, ast.GeneratorExp)):
                # Alcance aparte: sus variables no son del módulo. Lo único
                # que sí se evalúa acá afuera es el iterable más externo.
                if isinstance(n, ast.Lambda):
                    for d in n.args.defaults:
                        pila.append(d)
                else:
                    if n.generators:
                        pila.append(n.generators[0].iter)
                continue
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in conocidos and n.id not in definidos:
                    problemas.append((n.id, n.lineno))
                continue
            pila.extend(ast.iter_child_nodes(n))

    def recorrer(cuerpo):
        for s in cuerpo:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in s.decorator_list:
                    usar(d)
                for d in s.args.defaults + [x for x in s.args.kw_defaults if x]:
                    usar(d)
                definidos.setdefault(s.name, s.lineno)
            elif isinstance(s, ast.ClassDef):
                for d in s.decorator_list:
                    usar(d)
                for b in s.bases:
                    usar(b)
                definidos.setdefault(s.name, s.lineno)
            elif isinstance(s, (ast.Import, ast.ImportFrom)):
                for a in s.names:
                    definidos.setdefault((a.asname or a.name).split(".")[0], s.lineno)
            elif isinstance(s, ast.If):
                usar(s.test); recorrer(s.body); recorrer(s.orelse)
            elif isinstance(s, (ast.For, ast.AsyncFor)):
                usar(s.iter); registrar(s.target); recorrer(s.body); recorrer(s.orelse)
            elif isinstance(s, ast.While):
                usar(s.test); recorrer(s.body); recorrer(s.orelse)
            elif isinstance(s, (ast.With, ast.AsyncWith)):
                for it in s.items:
                    usar(it.context_expr); registrar(it.optional_vars)
                recorrer(s.body)
            elif isinstance(s, ast.Try):
                recorrer(s.body)
                for h in s.handlers:
                    usar(h.type)
                    if h.name:
                        definidos.setdefault(h.name, h.lineno)
                    recorrer(h.body)
                recorrer(s.orelse); recorrer(s.finalbody)
            elif isinstance(s, ast.Assign):
                usar(s.value); registrar(s.targets[0] if s.targets else None)
                for tg in s.targets[1:]:
                    registrar(tg)
            elif isinstance(s, (ast.AugAssign, ast.AnnAssign)):
                usar(getattr(s, "value", None)); usar(s.target); registrar(s.target)
            else:
                for hijo in ast.iter_child_nodes(s):
                    usar(hijo)

    recorrer(arbol.body)
    # Un nombre que nunca se define en el módulo viene de otro lado (un
    # import con *, un builtin que no listamos): no es este bug.
    return [(n, ln, definidos[n]) for n, ln in problemas if n in definidos]


APP = os.path.join(RAIZ, "app.py")

print("\n== Arranque de la app Python ==")


@test("app.py no usa ningún nombre antes de definirlo (a nivel de módulo)")
def _():
    malos = nombres_usados_antes_de_definirse(APP)
    detalle = "; ".join(f"'{n}' se usa en la línea {u} y se define en la {d}"
                        for n, u, d in malos)
    assert not malos, f"la app va a morir con NameError: {detalle}"


@test("los otros módulos del producto tampoco")
def _():
    malos = {}
    for f in sorted(os.listdir(RAIZ)):
        if not f.endswith(".py") or f == "app.py":
            continue
        r = nombres_usados_antes_de_definirse(os.path.join(RAIZ, f))
        if r:
            malos[f] = r
    assert not malos, f"{malos}"


@test("app.py compila (sintaxis válida)")
def _():
    import py_compile, tempfile
    with tempfile.TemporaryDirectory() as d:
        py_compile.compile(APP, doraise=True, cfile=os.path.join(d, "app.pyc"))


@test("app.py arranca de verdad y no tira excepciones")
def _():
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("      (streamlit no instalado: se saltea el arranque real)")
        return

    # El EULA y la marca de trial se guardan al lado del código, así que
    # el estado de una corrida anterior cambiaría el resultado de esta.
    marcas = [os.path.join(RAIZ, ".eula_aceptado"), os.path.join(RAIZ, ".mvsql_trial.json")]
    previos = {m: (open(m, "rb").read() if os.path.exists(m) else None) for m in marcas}
    for m in marcas:
        if os.path.exists(m):
            os.remove(m)
    try:
        at = AppTest.from_file(APP, default_timeout=240)
        at.run()
        assert not at.exception, f"revienta en la pantalla del EULA: {[e.value for e in at.exception]}"
        assert at.checkbox, "no aparece el checkbox del EULA"

        at.checkbox[0].check().run()
        at.button[0].click().run()
        assert not at.exception, \
            f"revienta apenas el cliente acepta el EULA: {[e.value for e in at.exception]}"
        # Si entró de verdad, la barra lateral tiene sus selectores.
        assert len(at.selectbox) >= 4, \
            f"aceptó el EULA pero la app no cargó (solo {len(at.selectbox)} selectores)"
    finally:
        for m, contenido in previos.items():
            if contenido is None:
                if os.path.exists(m):
                    os.remove(m)
            else:
                open(m, "wb").write(contenido)


@test("el primer arranque de un cliente en prueba NO muestra errores rojos")
def _():
    """
    El proveedor de IA que viene primero en la lista es "MV SQL Créditos",
    que solo funciona en el zip comprado. Como el selectbox no llevaba
    index=, quedaba preseleccionado, y lo primero que veía alguien en
    prueba era un error rojo sobre un producto que todavía no compró — en
    su primer minuto con la app, antes de haber consultado nada.

    Se prueban las dos ramas porque arreglar una sola rompe la otra: sin
    licencia tiene que ofrecer un proveedor donde pueda pegar su API key,
    y con licencia tiene que ofrecer el que pagó.
    """
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("      (streamlit no instalado: se saltea)")
        return

    import json
    marcas = [os.path.join(RAIZ, n) for n in
              (".eula_aceptado", ".mvsql_trial.json", "licencia_mvsql.json")]
    previos = {m: (open(m, "rb").read() if os.path.exists(m) else None) for m in marcas}
    lic = os.path.join(RAIZ, "licencia_mvsql.json")

    def arrancar():
        for m in marcas[:2]:
            if os.path.exists(m):
                os.remove(m)
        at = AppTest.from_file(APP, default_timeout=240)
        at.run()
        at.checkbox[0].check().run()
        at.button[0].click().run()
        sel = [s for s in at.selectbox if s.label and "IA" in s.label]
        return at, (sel[0].value if sel else None)

    try:
        # 1) Cliente en prueba: sin licencia de creditos.
        if os.path.exists(lic):
            os.remove(lic)
        at, prov = arrancar()
        assert not at.error, \
            f"el cliente en prueba ve un error rojo al entrar: {[str(e.value)[:120] for e in at.error]}"
        assert prov == "anthropic", f"preselecciona '{prov}', que no puede usar sin comprar"

        # 2) Cliente que compro creditos: ahi si corresponde el proveedor pago.
        with open(lic, "w", encoding="utf-8") as fh:
            json.dump({"producto": "MV SQL NLP", "plan": "profesional", "mode": "credits",
                       "creditos": 500, "email": "x@y.com",
                       "vence": "2099-12-31T00:00:00+00:00"}, fh)
        at, prov = arrancar()
        assert prov == "mvsql_creditos", \
            f"compro creditos y le preselecciona '{prov}': tiene que buscarlo a mano"
        assert not at.error, "el cliente con creditos ve un error"
    finally:
        for m, contenido in previos.items():
            if contenido is None:
                if os.path.exists(m):
                    os.remove(m)
            else:
                open(m, "wb").write(contenido)


print(f"\n  {_pasadas} pasadas · {_falladas} falladas\n")
sys.exit(1 if _falladas else 0)
