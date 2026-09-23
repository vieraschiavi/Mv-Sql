# © 2026 Martín Viera. Todos los derechos reservados.

# MV SQL NLP — modo servidor
# ============================================================================
# La app corre acá adentro, en la infraestructura del cliente. Quien la usa
# entra SOLO por el navegador: al navegador viaja HTML, nunca la base. Esa es
# la diferencia que importa y es estructural, no una promesa — no hay ningún
# camino por el que los datos del cliente lleguen a la máquina del consultor.
#
# Todo lo que la app escribe (credenciales de conexión, auditoría, equipo,
# licencia) cae en /datos, que es un volumen del cliente. Cuando el trabajo
# termina, se borra ese volumen y no queda nada en ningún lado.
# ============================================================================

FROM python:3.11-slim

# Driver ODBC de Microsoft para SQL Server. Va en un ARG y no fijo porque
# agrega ~100 MB y una EULA de Microsoft que hay que aceptar: si el cliente
# es MySQL o PostgreSQL, no tiene por qué cargar con eso.
#   docker build --build-arg SQLSERVER=0 ...
ARG SQLSERVER=1

# curl y gnupg solo para traer la clave del repo de Microsoft; se van en la
# misma capa. build-essential NO hace falta: pymysql es Python puro y
# psycopg2-binary viene compilado.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg ca-certificates \
 && if [ "$SQLSERVER" = "1" ]; then \
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
          | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg && \
        echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft.gpg] \
https://packages.microsoft.com/debian/12/prod bookworm main" \
          > /etc/apt/sources.list.d/microsoft.list && \
        apt-get update && \
        ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc; \
    fi \
 && apt-get purge -y curl gnupg && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Las dependencias primero y el código después: cambiar una línea de app.py
# no vuelve a bajar 400 MB de ruedas.
COPY app-python/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir pymysql psycopg2-binary \
 && if [ "$SQLSERVER" = "1" ]; then pip install --no-cache-dir pyodbc; fi

COPY app-python/ /app/

# El preparador de propietario viaja adentro para poder correrlo contra el
# volumen sin salir del contenedor:
#     docker compose exec mvsql python /app/preparar-propietario.py
# Se lleva su dependencia (la definición de la licencia) para no duplicarla:
# hay UNA sola en todo el repo y las dos formas de instalar la heredan.
COPY servidor/preparar-propietario.py /app/preparar-propietario.py
COPY tools/generar_conversor_owner.py /app/tools/generar_conversor_owner.py

# El estado NO va en /app: /app es código, se pisa entero en cada build.
# /datos es del cliente y sobrevive a las actualizaciones de la imagen.
ENV MVSQL_DATOS=/datos
RUN mkdir -p /datos

# Usuario sin privilegios. Si alguien encuentra un agujero en la app, que no
# esté parado en root dentro de la red del cliente.
RUN useradd --system --uid 10001 mvsql && chown -R mvsql:mvsql /app /datos
USER mvsql

EXPOSE 8791

# El healthcheck usa el endpoint propio de Streamlit, no la portada: la
# portada devuelve 200 aunque la app haya reventado por dentro.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8791/_stcore/health', timeout=4)\
.read().strip()==b'ok' else 1)"

# --server.address 0.0.0.0 es DENTRO del contenedor. Quién llega desde afuera
# lo decide el mapeo de puertos del compose, que por defecto publica solo en
# 127.0.0.1 del host.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8791", "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false", \
     "--server.enableXsrfProtection=true", \
     "--server.enableCORS=false"]
