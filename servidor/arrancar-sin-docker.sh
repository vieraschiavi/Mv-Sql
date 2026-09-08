#!/usr/bin/env bash
# © 2026 Martín Viera. Todos los derechos reservados.
#
# MV SQL NLP en modo servidor, SIN Docker.
# ============================================================================
# Para el servidor o la VM de un cliente que tiene Python pero no deja
# instalar Docker (o donde pedirlo abre un ticket de tres semanas).
#
#   ./arrancar-sin-docker.sh /srv/mvsql-datos
#
# El argumento es la carpeta donde queda TODO lo que la app escribe:
# credenciales de conexión, auditoría, equipo, licencia. Terminado el
# trabajo, se borra esa carpeta y no queda nada.
#
# Por defecto escucha SOLO en 127.0.0.1: desde afuera se llega con un túnel
# SSH. Para publicarlo en la red interna del cliente:
#
#   MVSQL_BIND=0.0.0.0 ./arrancar-sin-docker.sh /srv/mvsql-datos
#
# Antes de hacer eso, leer docs/MODO_SERVIDOR.md — sin equipo con PIN
# creado, cualquiera de esa red entra a la base del cliente.
# ============================================================================

set -euo pipefail

DATOS="${1:-}"
if [ -z "$DATOS" ]; then
  echo "Uso: $0 /ruta/a/la/carpeta-de-datos" >&2
  echo "" >&2
  echo "Esa carpeta es la que se borra cuando termina el trabajo en el" >&2
  echo "cliente. Poner una ruta dedicada, no el home ni /tmp." >&2
  exit 2
fi

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$(cd "$AQUI/.." && pwd)/app-python"
VENV="$AQUI/.venv"
PUERTO="${MVSQL_PUERTO:-8791}"
BIND="${MVSQL_BIND:-127.0.0.1}"

mkdir -p "$DATOS"

if [ ! -d "$VENV" ]; then
  echo "==> Creando el entorno virtual (una sola vez)"
  python3 -m venv "$VENV"
fi

echo "==> Instalando dependencias"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$APP/requirements.txt"
# Los drivers de base van aparte porque no todos los clientes usan todos, y
# porque pyodbc además necesita el driver ODBC del sistema operativo (en
# Debian/Ubuntu: msodbcsql18). Si alguno falla, la app arranca igual y solo
# queda sin ESE motor — no se cae la instalación entera.
for paquete in pymysql psycopg2-binary pyodbc; do
  "$VENV/bin/pip" install --quiet "$paquete" 2>/dev/null \
    || echo "    (aviso: no se pudo instalar $paquete — ese motor queda sin usar)"
done

echo
echo "==> Datos del cliente en: $DATOS"
echo "==> Escuchando en:        http://$BIND:$PUERTO"
if [ "$BIND" = "127.0.0.1" ]; then
  echo "    Solo local. Desde tu laptop, con un túnel:"
  echo "      ssh -L $PUERTO:127.0.0.1:$PUERTO usuario@$(hostname)"
  echo "      y después abrí http://localhost:$PUERTO en el navegador"
else
  echo "    ATENCIÓN: expuesto a la red. Creá el equipo con PIN antes de"
  echo "    conectar una base real (docs/MODO_SERVIDOR.md)."
fi
echo

cd "$APP"
exec env MVSQL_DATOS="$DATOS" "$VENV/bin/streamlit" run app.py \
  --server.port="$PUERTO" \
  --server.address="$BIND" \
  --server.headless=true \
  --browser.gatherUsageStats=false \
  --server.enableXsrfProtection=true \
  --server.enableCORS=false
