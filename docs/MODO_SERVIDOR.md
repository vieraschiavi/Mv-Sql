# © 2026 Martín Viera. Todos los derechos reservados.

# Modo servidor — trabajar en el cliente sin llevarte sus datos

Este modo existe para un caso puntual y muy concreto:

> Una contratista te pone en un proyecto para un cliente. Los datos del cliente
> **no pueden terminar en tu laptop**, ni en la de tu empleadora. Y tu laptop de
> trabajo, además, no te deja instalar programas.

La app corre en un servidor o contenedor **del cliente**, y vos entrás solo con
el navegador. Al navegador viaja HTML: la base nunca sale de la infraestructura
del cliente. Cuando el trabajo termina, se borra el volumen y no queda nada en
ningún lado.

---

## Primero, la parte incómoda

**Un programa tiene que correr en algún lado.** No existe forma de consultar la
base de un cliente sin que haya un proceso ejecutándose en alguna máquina. Si
el cliente no te da *nada* donde ejecutar —ni servidor, ni VM, ni contenedor, ni
una carpeta en un equipo suyo— entonces no hay solución técnica, ni de este
producto ni de ningún otro. Eso hay que negociarlo antes de empezar, no
resolverlo con software.

Ahora, la buena noticia: **eso no es un requisito nuevo que trae MV SQL NLP.**
Para consultar la base del cliente ya necesitás acceso a su red. Un contenedor
o una carpeta con Python en un servidor suyo es, casi siempre, más fácil de
conseguir que permiso para instalar software en la laptop corporativa.

Y hay un detalle que conviene decir en voz alta cuando lo negociás: **este modo
le da al cliente más control, no menos.** Los datos no salen de su
infraestructura, la app es de solo lectura sobre su base, y queda una auditoría
—en su servidor— de quién consultó qué. Comparado con un consultor bajando
extractos a Excel en su propia laptop, es lo contrario a un riesgo.

---

## Por qué las otras formas no sirven acá

| Forma | Por qué no |
|---|---|
| **Instalada** (`MV-SQL-NLP-App-Setup.exe`) | La laptop corporativa no deja instalar. Y aunque dejara, los datos quedarían en tu perfil. |
| **Portable** (`MV-SQL-NLP-Portable.exe`) | No necesita instalador, pero **sigue ejecutándose en tu laptop**: las credenciales del cliente y cualquier archivo que importes quedan en la carpeta del `.exe`. Resuelve el problema del permiso, no el de la confidencialidad. |
| **Modo servidor** | Lo único donde "los datos no tocan mi máquina" es **estructural** y no una promesa: no hay ningún camino de código por el que puedan llegar. |

La portable sigue siendo la correcta cuando la máquina es del cliente y sos vos
quien la usa (ver `FORMAS_DE_INSTALAR.md`). El modo servidor es para cuando la
máquina donde trabajás **no puede tener los datos**.

---

## Cómo se levanta

### Con Docker (lo más limpio)

En el servidor del cliente:

```bash
git clone <este repo>          # o copiar la carpeta
cd Mv-Sql/servidor
docker compose up -d --build
```

Y para dejarlo listo como propietario (sin trial, sin pedir licencia):

```bash
docker compose exec mvsql python /app/preparar-propietario.py
```

Desde tu laptop, un túnel SSH y el navegador:

```bash
ssh -L 8791:127.0.0.1:8791 usuario@servidor-del-cliente
# después: http://localhost:8791
```

Si el cliente no usa SQL Server, la imagen baja ~100 MB y se saltea la EULA del
driver de Microsoft:

```bash
MVSQL_SQLSERVER=0 docker compose up -d --build
```

### Sin Docker (servidor con Python)

```bash
./servidor/arrancar-sin-docker.sh /srv/mvsql-datos
```

El argumento es la carpeta donde queda todo el estado. Lo demás —entorno
virtual, dependencias, drivers— lo arma el script.

---

## Dónde queda cada cosa

Todo lo que la app escribe cae en **una sola carpeta**, la que decide
`MVSQL_DATOS` (`/datos` dentro del contenedor, el volumen `mvsql-datos` en el
host):

| Archivo | Qué es |
|---|---|
| `licencia_mvsql.json` | La licencia |
| `equipo.json` | Usuarios, roles y PINes (PBKDF2-SHA256, nunca en texto plano) |
| `auditoria.db` | Quién consultó qué, cuándo, con qué SQL y qué resultado |
| `consultas_guardadas.json` | Consultas guardadas |
| `.eula_aceptado` | Marca de aceptación del EULA |

**Las credenciales de la base del cliente van adentro de `equipo.json`/la
configuración de conexión — o sea, en el volumen del cliente.** No están en el
`docker-compose.yml` a propósito: un compose se commitea, se copia y se manda
por chat; un secreto adentro se filtra solo.

Para borrar todo, un comando:

```bash
docker compose down -v      # la -v es la que se lleva los datos
```

Sin Docker: `rm -rf /srv/mvsql-datos`.

---

## Antes de abrirlo a la red

Por defecto el puerto se publica **solo en `127.0.0.1`** del servidor: nadie más
en la red del cliente lo ve. Se llega por túnel SSH, que además viaja cifrado.

Si el equipo del cliente lo va a usar y hace falta exponerlo (`MVSQL_BIND=0.0.0.0`),
**primero hay que crear el equipo con PIN**. Sin eso, cualquiera que llegue a ese
puerto entra a la base del cliente sin credencial:

1. Levantar con el bind por defecto.
2. Entrar por el túnel y crear los usuarios en "Equipo y permisos" — cada uno
   con su PIN y con las tablas que su rol puede ver.
3. Recién ahí cambiar el bind.

Y aunque esté con PIN: un puerto HTTP en una red corporativa viaja sin cifrar.
Si el cliente lo va a exponer más allá de un segmento controlado, que lo ponga
detrás de su reverse proxy con TLS. Eso es infraestructura del cliente y no
algo que este repo deba resolver por él.

---

## Lo que el contenedor ya trae puesto

| Medida | Por qué |
|---|---|
| `read_only: true`, con `/tmp` y la config de Streamlit en tmpfs | El contenedor no puede escribirse a sí mismo; lo único persistente es el volumen de datos |
| `cap_drop: ALL`, `no-new-privileges` | Si aparece un agujero en la app, que no esté parado en root dentro de la red del cliente |
| Usuario `mvsql` (uid 10001), no root | Lo mismo |
| `browser.gatherUsageStats=false` | Streamlit por defecto manda telemetría afuera. En la red de un cliente eso es una llamada saliente que nadie pidió |
| `enableXsrfProtection=true`, `enableCORS=false` | Que otra pestaña del navegador no pueda hacerle pedidos |
| Healthcheck contra `/_stcore/health` | La portada devuelve 200 aunque la app haya reventado por dentro |

Y lo que ya traía el producto y acá importa el doble: **toda conexión se abre en
solo lectura** y el motor rechaza cualquier SQL que no empiece con `SELECT` o
`WITH`. No hay camino de ejecución que haga INSERT, UPDATE, DELETE ni DDL sobre
la base del cliente.

---

## Lo que este modo NO resuelve

Vale decirlo explícito, porque son las preguntas que va a hacer el área de
seguridad del cliente:

- **La IA sigue siendo una llamada saliente.** El esquema (nombres de tablas y
  columnas) viaja al proveedor que elijas para que genere el SQL. Con el **modo
  privacidad estricta** activado no viaja ni una fila de datos; sin él, el
  análisis escrito manda una muestra de hasta 20 filas del resultado. Si el
  cliente no acepta ninguna salida a internet, la opción es **Ollama local** en
  el mismo servidor — ahí no sale nada.
- **Exportar sigue siendo bajar un archivo.** Si desde el navegador exportás a
  Excel o PDF, ese archivo baja a tu laptop. El modo servidor evita que los
  datos lleguen ahí *solos*; no puede evitar que alguien los baje a propósito.
  Para eso está la auditoría, que registra quién exportó qué, y los permisos por
  rol, que le sacan la exportación a quien no deba tenerla.
- **Quien tenga acceso al servidor tiene acceso al volumen.** El estado está en
  claro en el disco del cliente. Es su disco y sus políticas: cifrado en reposo,
  backups y quién puede entrar al host son decisiones suyas.
