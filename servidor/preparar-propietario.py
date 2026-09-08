# © 2026 Martín Viera. Todos los derechos reservados.

"""
preparar-propietario.py — deja el modo servidor listo para el propietario
==================================================================
Escribe, en la carpeta de datos del servidor, las dos marcas que hacen
que la app arranque DIRECTO en la pantalla de conexión: la licencia de
propietario (sin trial, sin cartel de comprar) y el EULA aceptado.

Por qué una licencia y no una variable de entorno tipo MVSQL_PROPIETARIO:
este repositorio es público. Una variable de entorno que saltee el
control sería un bypass documentado — cualquiera que lea el código la
pone y usa el producto gratis para siempre. La licencia reusa el
mecanismo que ya existe (licencia.py sólo mira `vence`), sin agregar un
camino nuevo por donde escaparse.

Y por qué "no escribe ni pide licencia" sigue siendo cierto en marcha:
con una licencia vigente, verificar_acceso() corta en la primera línea y
NO crea la marca de trial. O sea que esto se corre UNA vez al montar el
servidor, y de ahí en más la app no escribe nada relacionado a licencias
ni le pregunta nada a nadie.

    # dentro del contenedor
    docker compose exec mvsql python /app/preparar-propietario.py

    # o, más simple, contra el volumen desde el host:
    MVSQL_DATOS=/ruta/al/volumen python3 servidor/preparar-propietario.py

Es para las instalaciones del propietario. No repartirlo: no vence nunca.
==================================================================
"""

import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(_AQUI)

# Este script corre en DOS layouts distintos y tiene que andar en los dos:
#
#   - el repo:      servidor/preparar-propietario.py, con app-python/ y
#                   tools/ como hermanas de servidor/
#   - la imagen:    /app/preparar-propietario.py, al lado de los módulos
#                   de la app, con generar_conversor_owner.py en /app/tools/
#
# Por eso se prueban varios candidatos en vez de asumir uno. Se agregan solo
# los que existen: un sys.path con rutas fantasma esconde un import roto
# atrás de un ModuleNotFoundError que no dice cuál de los dos layouts falló.
for _cand in (_AQUI,
              os.path.join(RAIZ, "app-python"),
              os.path.join(RAIZ, "tools"),
              os.path.join(_AQUI, "tools")):
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)

import rutas  # noqa: E402

# Una sola definición de la licencia de propietario en todo el repo. Si
# algún día se le agrega una firma, cambia en un solo lugar y este script
# la hereda en vez de quedar generando licencias inválidas en silencio.
from generar_conversor_owner import LICENCIA  # noqa: E402


def main():
    destino = rutas.carpeta_datos()
    if not os.environ.get(rutas.VARIABLE, "").strip():
        print(f"Ojo: {rutas.VARIABLE} no está puesta, así que esto escribiría en")
        print(f"  {destino}")
        print("que es la carpeta del código, no el volumen del servidor.")
        print(f"Corrélo así:  {rutas.VARIABLE}=/ruta/al/volumen python3 {sys.argv[0]}")
        return 1

    ruta_licencia = os.path.join(destino, "licencia_mvsql.json")
    with open(ruta_licencia, "w", encoding="utf-8") as fh:
        json.dump(LICENCIA, fh, ensure_ascii=False, indent=2)
    print(f"✓ licencia de propietario  → {ruta_licencia}")

    # El EULA se acepta una vez por instalación. Sin esto la app abre en
    # esa pantalla, que en un servidor sin teclado a mano es una molestia
    # sin sentido: el propietario está aceptando su propio acuerdo.
    import eula
    eula.registrar_aceptacion()
    print(f"✓ EULA aceptado            → {eula.RUTA_MARCA_EULA}")

    print()
    print("Listo. La app arranca en la pantalla de conexión, sin trial y sin")
    print("pedir licencia. Todo esto vive en el volumen del cliente: se borra")
    print("entero con `docker compose down -v`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
