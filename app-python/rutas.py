# © 2026 Martín Viera. Todos los derechos reservados.

"""
rutas.py — dónde se guarda el estado de la app
==================================================================
Un solo lugar decide en qué carpeta van los archivos que la app
escribe: el equipo, la auditoría, la licencia, la marca del EULA y las
consultas guardadas. Antes cada módulo lo resolvía por su cuenta con
`os.path.dirname(__file__)`, así que el estado quedaba siempre mezclado
con el código fuente.

Eso alcanza cuando la app corre instalada en la PC de quien la usa. No
alcanza en modo servidor, que es el caso que motivó este módulo:

    Un consultor entra a trabajar a un cliente. Los datos del cliente
    —las credenciales de su base, la auditoría de quién consultó qué—
    NO pueden terminar en la laptop del consultor. Tienen que quedar
    en la infraestructura del cliente, y borrarse enteros cuando el
    trabajo termina.

Con la app corriendo en un servidor o contenedor del cliente y el
consultor entrando solo por el navegador, eso se cumple estructuralmente
(no por promesa): al navegador viaja HTML, no la base. Pero para que el
cliente pueda montar UNA carpeta y llevarse/borrar todo el estado de una
vez, el estado tiene que estar junto y separado del código. Para eso
está MVSQL_DATOS.

Espejo deliberado de desktop/electron/services/rutas.cjs, que resuelve
exactamente el mismo problema del lado de Electron con
PORTABLE_EXECUTABLE_DIR. Los dos productos guardan lo mismo y tienen que
poder sacarlo de la máquina de la misma manera.

    MVSQL_DATOS=/datos  streamlit run app.py

Sin la variable, NADA cambia: el estado sigue cayendo al lado del código,
que es donde lo dejan el instalador NSIS y la app de Electron. Eso no es
pereza — mover el default rompería las instalaciones que ya existen, que
tienen su licencia_mvsql.json escrito ahí.
==================================================================
"""

import os

_DIR_APP = os.path.dirname(os.path.abspath(__file__))

#: Nombre de la variable de entorno. Como constante para que los tests
#: no la escriban a mano y un typo se note al importar, no al fallar.
VARIABLE = "MVSQL_DATOS"


def carpeta_datos():
    """La carpeta donde va TODO lo que la app escribe.

    Con MVSQL_DATOS puesta, esa carpeta (se crea si no existe). Sin la
    variable, la carpeta del código — el comportamiento de siempre.

    Si la variable apunta a algo que no se puede crear (permisos, disco
    de solo lectura), NO se rompe la app: se avisa y se cae al default.
    Plantarse en el arranque por esto dejaría al consultor sin programa
    en medio de una visita al cliente, y el default sigue siendo un
    lugar que funciona.
    """
    destino = os.environ.get(VARIABLE, "").strip()
    if not destino:
        return _DIR_APP

    destino = os.path.abspath(os.path.expanduser(destino))
    try:
        os.makedirs(destino, exist_ok=True)
    except OSError as e:
        print(f"[MV SQL NLP] No se pudo usar {VARIABLE}={destino} ({e}). "
              f"El estado va a {_DIR_APP}.")
        return _DIR_APP
    return destino


def en_datos(nombre):
    """Ruta completa de un archivo de estado dentro de carpeta_datos()."""
    return os.path.join(carpeta_datos(), nombre)
