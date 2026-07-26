"""
empaquetar_zip.py — arma el zip que descarga el cliente.
==================================================================
`web/downloads/mvsql-nlp-app.zip` es lo que se entrega después de la
compra. Antes se pisaba a mano, así que quedaba desactualizado respecto
de `app-python/` sin que nadie se enterara. Esto lo arma siempre igual.

Deja afuera lo que no le sirve al cliente (tests, caché, la base demo
que se genera sola en el primer arranque) y lo que es dato privado
(equipo.json, auditoria.db, licencia_mvsql.json).

    python tools/empaquetar_zip.py
==================================================================
"""

import os
import zipfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ORIGEN = os.path.join(RAIZ, "app-python")
DESTINO = os.path.join(RAIZ, "web", "downloads", "mvsql-nlp-app.zip")
CARPETA = "nl2sql_rag"          # nombre de la carpeta dentro del zip

INCLUIR = (".py", ".txt", ".bat", ".ico")
EXCLUIR = {
    "cartera_demo.db",          # se genera sola en el primer arranque
    "catalogo_demo.json",
    "equipo.json",              # datos del cliente
    "auditoria.db",
    "licencia_mvsql.json",      # la agrega el backend según lo comprado
    ".idioma",
    ".accesos_ok",
}
CARPETAS_FUERA = {"tests", "__pycache__", ".venv"}


def archivos():
    for nombre in sorted(os.listdir(ORIGEN)):
        ruta = os.path.join(ORIGEN, nombre)
        if os.path.isdir(ruta):
            if nombre not in CARPETAS_FUERA:
                print(f"  (se omite la carpeta {nombre}/)")
            continue
        if nombre in EXCLUIR or not nombre.endswith(INCLUIR):
            continue
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

    faltan = [n for n in ("INICIAR_MVSQL.bat", "CONECTAR_CLAUDE_MCP.bat",
                          "app.py", "LEEME.txt", "requirements.txt", "mvsql.ico")
              if n not in metidos]
    if faltan:
        raise SystemExit(f"✗ Falta empaquetar: {faltan}")


if __name__ == "__main__":
    main()
