# © 2026 Martín Viera. Todos los derechos reservados.

"""
fuente.py — la FUENTE ACTIVA: contra qué base trabaja la app
==================================================================
Una sola respuesta a «¿contra qué datos corre esto?», que leen TODAS las
partes de la app: la consulta en lenguaje natural, los cuadernos, el
diagrama de relaciones, el esquema, la frescura, el plan de ejecución, el
panel Explorar, la gestión de tablas del equipo y los exportes.

Hay dos tipos de fuente:

  - "demo":    la base sintética cartera_demo.db (generar_db_demo.py).
               Es lo que se ve cuando el cliente todavía no conectó nada.
  - "usuario": lo que el cliente eligió — un archivo (CSV/Excel/Parquet/
               JSON convertido a SQLite) o su base SQL.

Por qué existe: antes la conexión vivía suelta en session_state y cada
parte de la pantalla guardaba sus propios derivados (el último resultado,
la frescura, las tablas elegidas en el diagrama o en Explorar, el
historial). Al conectar la base propia, la conexión cambiaba pero esos
derivados seguían mostrando la demo: el cliente subía su archivo y seguía
viendo el resultado, la frescura y los ejemplos de cobranzas de la base
sintética. Acá el cambio de fuente y la limpieza de TODO lo derivado son
una sola operación, así que no se puede hacer una sin la otra.

Regla: el único que escribe estado["motor"] es este módulo. El resto de
la app solo lo lee (con motor()).

No importa Streamlit: `estado` es cualquier mapeo (st.session_state en la
app, un dict en los tests).
==================================================================
"""

import os

DEMO = "demo"
USUARIO = "usuario"

#: Dónde está la base demo. generar_db_demo.py la escribe en la carpeta de
#: trabajo, y INICIAR_MVSQL.bat corre todo desde la carpeta de la app.
#: Es variable de módulo para que los tests la apunten a una base propia.
RUTA_DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "cartera_demo.db")

#: Todo lo que se calcula A PARTIR de la fuente y se guarda entre reruns.
#: Se borra cada vez que la fuente cambia: si sobreviviera, mostraría
#: datos de la base anterior al lado de la nueva. Incluye las claves de
#: los widgets que ofrecen tablas o columnas (diagrama, Explorar, equipo,
#: gráfico), que si no quedan con opciones de la base anterior.
DERIVADOS = (
    "resultado", "frescura", "historial", "pregunta_precargada",
    "sql_directo", "diag_tablas", "eda_fuente", "eda_objetivo",
    "eq_tablas", "graf_x", "graf_y", "tipo_grafico",
)

# Valor "vacío" de los derivados que la app lee sin .get()
_VACIO = {"historial": [], "pregunta_precargada": "", "resultado": None}


def motor(estado):
    """EL resolvedor: el motor (conexión + catálogo) de la fuente activa, o None."""
    return estado.get("motor")


def activa(estado):
    """Descripción de la fuente activa: {"tipo", "etiqueta", "id"} o None."""
    return estado.get("fuente")


def es_demo(estado):
    f = activa(estado)
    return bool(f) and f.get("tipo") == DEMO


def es_ruta_demo(ruta):
    """¿Esta ruta de SQLite es la base demo? (conectarla a mano sigue siendo demo)."""
    if not ruta:
        return False
    try:
        return os.path.realpath(ruta) == os.path.realpath(RUTA_DEMO)
    except OSError:
        return False


def invalidar(estado):
    """Borra todo lo derivado de la fuente anterior."""
    for clave in DERIVADOS:
        if clave in _VACIO:
            estado[clave] = type(_VACIO[clave])() if _VACIO[clave] is not None else None
        elif clave in estado:
            del estado[clave]


def _cerrar_anterior(estado, nuevo=None):
    anterior = estado.get("motor")
    if anterior is None or anterior is nuevo:
        return
    cx = getattr(anterior, "cx", None)
    if hasattr(cx, "cerrar"):
        try:
            cx.cerrar()
        except Exception:
            pass    # la conexión vieja ya no importa; no frena el cambio


def _poner(estado, motor_nuevo, tipo, etiqueta, ident):
    _cerrar_anterior(estado, motor_nuevo)
    estado["motor"] = motor_nuevo
    estado["fuente"] = ({"tipo": tipo, "etiqueta": etiqueta, "id": ident}
                        if motor_nuevo is not None else None)
    invalidar(estado)


def usar_usuario(estado, motor_nuevo, etiqueta, ident=None):
    """Activa la fuente del cliente. Reemplaza a la demo en TODA la app."""
    tipo = USUARIO
    cx = getattr(motor_nuevo, "cx", None)
    if getattr(cx, "motor", None) == "sqlite" and es_ruta_demo(getattr(cx, "ruta", None)):
        tipo = DEMO     # conectó cartera_demo.db a mano: el indicador no miente
    _poner(estado, motor_nuevo, tipo, etiqueta, ident or etiqueta)


def usar_demo(estado, fabricar):
    """Vuelve a la base demo.

    `fabricar(ruta)` arma el motor para una ruta SQLite (la app aplica ahí
    el recorte de tablas por rol). Si la demo no existe o no abre, queda
    SIN fuente —nunca con la anterior colgada— y devuelve False.
    """
    if not os.path.exists(RUTA_DEMO):
        _poner(estado, None, None, None, None)
        return False
    try:
        m = fabricar(RUTA_DEMO)
    except Exception:
        _poner(estado, None, None, None, None)
        return False
    _poner(estado, m, DEMO, os.path.basename(RUTA_DEMO), RUTA_DEMO)
    return True


def asegurar(estado, fabricar):
    """Al abrir la app sin fuente elegida, arranca con la demo (si existe).

    Solo actúa la PRIMERA vez (o después de olvidar()): si el cliente ya
    tiene su fuente, no se toca.
    """
    if estado.get("_fuente_inicializada"):
        return
    estado["_fuente_inicializada"] = True
    if motor(estado) is None:
        usar_demo(estado, fabricar)


def olvidar(estado):
    """Suelta la fuente (p. ej. al cerrar sesión): el próximo rerun vuelve a la demo."""
    _poner(estado, None, None, None, None)
    estado["_fuente_inicializada"] = False


def ejemplos(estado, ejemplos_demo, plantillas, n=4):
    """Preguntas de ejemplo que tienen sentido para la fuente activa.

    Las de la demo hablan de cobranzas: mostradas con la base del cliente
    son una invitación a preguntar por tablas que no existen. Con una
    fuente propia se arman con SUS tablas.
    """
    m = motor(estado)
    if m is None or es_demo(estado):
        return list(ejemplos_demo)
    tablas = sorted((m.catalogo or {}).get("tablas", {}))
    if not tablas:
        return []
    salida = []
    i = 0
    while len(salida) < n and i < n * len(plantillas):
        tabla = tablas[i % len(tablas)]
        frase = plantillas[(i // len(tablas)) % len(plantillas)].format(tabla=tabla)
        if frase not in salida:
            salida.append(frase)
        i += 1
    return salida
