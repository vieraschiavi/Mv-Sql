"""
empaquetar_zip.py — arma el zip que descarga el cliente.
==================================================================
`web/downloads/mvsql-nlp-app.zip` es lo que se entrega después de la
compra. Antes se pisaba a mano, así que quedaba desactualizado respecto
de `app-python/` sin que nadie se enterara. Esto lo arma siempre igual.

Deja afuera lo que no le sirve al cliente (tests, caché, la base demo
que se genera sola en el primer arranque) y lo que es dato privado
(equipo.json, auditoria.db, licencia_mvsql.json).

Módulos protegidos (MODULOS_PROTEGIDOS): si tools/build_cython.py ya
corrió y dejó un `motor*.pyd` (Windows) al lado de motor.py, se empaqueta
el .pyd compilado en vez del .py fuente — así el cliente no recibe el
código en texto plano. Sin ese build (caso normal en una PC de
desarrollo sin Cython/MSVC), se empaqueta el .py como siempre: el
producto sigue funcionando igual, solo que sin esa capa extra. El
release real (CI en windows-latest) sí corre el build antes de llamar
a este script — ver .github/workflows/build-desktop.yml.

    python tools/empaquetar_zip.py
==================================================================
"""

import glob
import os
import zipfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ORIGEN = os.path.join(RAIZ, "app-python")
DESTINO = os.path.join(RAIZ, "web", "downloads", "mvsql-nlp-app.zip")
CARPETA = "nl2sql_rag"          # nombre de la carpeta dentro del zip

INCLUIR = (".py", ".txt", ".bat", ".ico", ".pyd")
EXCLUIR = {
    "cartera_demo.db",          # se genera sola en el primer arranque
    "catalogo_demo.json",
    "equipo.json",              # datos del cliente
    "auditoria.db",
    "licencia_mvsql.json",      # la agrega el backend según lo comprado
    ".idioma",
    ".accesos_ok",
    ".eula_aceptado",
    ".mvsql_trial.json",
}
CARPETAS_FUERA = {"tests", "__pycache__", ".venv", "build"}

# Módulos con "know-how" real (prompts, lógica del motor, trial): si
# build_cython.py dejó un .pyd compilado, se prioriza sobre el .py —
# nunca se empaquetan los dos (el .py en claro anularía la protección).
MODULOS_PROTEGIDOS = ("motor.py", "proveedores_ia.py", "licencia.py")


def _variante_a_empaquetar(nombre_py):
    """Para un módulo protegido: devuelve (nombre_en_zip, ruta) del .pyd
    compilado si existe, o del .py fuente si no."""
    base = nombre_py[:-3]
    compilados = sorted(glob.glob(os.path.join(ORIGEN, f"{base}*.pyd")))
    if compilados:
        ruta = compilados[0]
        return os.path.basename(ruta), ruta
    return nombre_py, os.path.join(ORIGEN, nombre_py)


def archivos():
    protegidos_listos = set()
    for nombre_py in MODULOS_PROTEGIDOS:
        nombre_final, ruta = _variante_a_empaquetar(nombre_py)
        protegidos_listos.add(nombre_py)
        if nombre_final == nombre_py:
            print(f"  (sin compilar: se empaqueta {nombre_py} en texto plano — "
                  f"correr tools/build_cython.py antes para el release protegido)")
        else:
            print(f"  (protegido: se empaqueta {nombre_final} en vez de {nombre_py})")
        yield nombre_final, ruta

    for nombre in sorted(os.listdir(ORIGEN)):
        if nombre in protegidos_listos:
            continue  # ya resuelto arriba (fuente o compilado)
        ruta = os.path.join(ORIGEN, nombre)
        if os.path.isdir(ruta):
            if nombre not in CARPETAS_FUERA:
                print(f"  (se omite la carpeta {nombre}/)")
            continue
        if nombre in EXCLUIR or not nombre.endswith(INCLUIR):
            continue
        if nombre.endswith(".pyd"):
            continue  # .pyd de un modulo protegido ya se resolvio arriba
        yield nombre, ruta


def main():
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    metidos = []
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo(f"{CARPETA}/"), b"")
        for nombre, ruta in archivos():
            # Los .bat entran byte a byte: llevan CRLF y solo ASCII a
            # propósito. Si se normalizan, cmd.exe cierra la ventana sola.
            z.write(ruta, f"{CARPETA}/{nombre}")
            metidos.append(nombre)

    total = os.path.getsize(DESTINO)
    print(f"\n✓ {os.path.relpath(DESTINO, RAIZ)}  ({total / 1024:.0f} KB, {len(metidos)} archivos)")
    for n in metidos:
        print(f"    {n}")

    # requirements-extras.txt tiene que viajar sí o sí: INICIAR_MVSQL.bat lo
    # instala después del núcleo, y si el archivo no está el paso de extras
    # falla en todos los arranques del cliente.
    faltan = [n for n in ("INICIAR_MVSQL.bat", "CONECTAR_CLAUDE_MCP.bat",
                          "app.py", "LEEME.txt", "requirements.txt",
                          "requirements-extras.txt", "mvsql.ico")
              if n not in metidos]
    if faltan:
        raise SystemExit(f"✗ Falta empaquetar: {faltan}")


if __name__ == "__main__":
    main()
