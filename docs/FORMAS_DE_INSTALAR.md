# © 2026 Martín Viera. Todos los derechos reservados.

# Las formas de instalar, y cuándo usar cada una

No son versiones distintas del producto: es el **mismo programa** puesto a
correr de tres maneras, según **de quién sea la máquina y de quién sean los
datos**.

| | **A · Instalada** | **B · Portable** | **C · En el servidor del cliente** |
|---|---|---|---|
| Para qué máquina | La tuya (o la del cliente que compró) | VM o laptop de un cliente donde sos consultor | Ninguna tuya: corre en infraestructura del cliente |
| Ejemplo | Tu PC · la notebook del cliente que pagó | La VM de Conaprole · la laptop que te da Practia | Practia te pone en Conaprole y sus datos no pueden tocar tu laptop |
| Necesita instalar | Sí (sin admin) | No: se copia y se ejecuta | **Nada en tu máquina**: entrás por el navegador |
| Necesita admin | **No** | **No** | En el servidor, lo que pida el cliente |
| Dónde van los datos | `%APPDATA%\MV SQL NLP` | Subcarpeta `datos-mvsql` **al lado del `.exe`** | **Un volumen del cliente. Nunca tocan tu máquina** |
| Al terminar | Queda instalada | Borrás la carpeta y en esa máquina no queda nada | `docker compose down -v` y no queda nada en ningún lado |

Las diferencias que importan, en una línea cada una:

- **B** no deja nada en la máquina del cliente.
- **C** no deja que los datos del cliente lleguen a la tuya — y eso es
  estructural, no una promesa: la app corre allá y al navegador viaja HTML.

Si tu laptop de trabajo no te deja instalar nada **y además** los datos del
cliente no pueden pasar por ella, la única que sirve es la **C**: ver
[MODO_SERVIDOR.md](MODO_SERVIDOR.md).

---

## A · Instalada (máquina propia o del cliente que compró)

### Producto de escritorio (Electron)

`MV-SQL-NLP-App-Setup.exe` → doble clic.

- **No pide permisos de administrador.** Instala en tu carpeta de usuario.
- **Elegís la carpeta** en la pantalla del instalador: no va por defecto a `C:`.
- Deja acceso directo en el escritorio y entrada en el menú Inicio.
- Se desinstala desde "Agregar o quitar programas" como cualquier programa.

### Producto Python / Streamlit

`MV-SQL-NLP-Setup.exe` → doble clic. Requiere Python en la máquina; el
instalador arma solo el entorno virtual, las dependencias y la base demo.

Alternativa sin instalador: el `.zip` y ejecutar `INICIAR_MVSQL.bat`.

### Dónde quedan los datos

`%APPDATA%\MV SQL NLP\` — conexiones guardadas, licencia, consultas guardadas.
Sobreviven a actualizar y a reinstalar, que es lo que se espera de un programa
instalado.

---

## B · Portable (VM o laptop de un cliente)

`MV-SQL-NLP-Portable-<version>.exe` → copiás el archivo a una carpeta (o a un
pendrique) y lo ejecutás. No instala nada.

### Qué hace distinto

Al arrancar crea `datos-mvsql\` **al lado del `.exe`** y guarda TODO ahí:

- `mvsql-store.json` — las conexiones guardadas
- `importado.db` — la copia de la base si importaste un Excel o CSV
- `licencia_mvsql.json` — tu licencia
- caché, cookies y almacenamiento interno de Electron

Cuando terminás el trabajo, **borrás esa carpeta** (o sacás el pendrive) y en
la máquina del cliente no queda absolutamente nada tuyo ni suyo.

### Por qué esto importa de verdad

Trabajando de consultor en la VM de un cliente, lo que se guarda no es
"configuración": son **las credenciales de conexión a la base del cliente**, una
**copia de sus datos** si importaste un archivo, y **tu licencia**. Dejar eso en
el perfil de una máquina que no es tuya es un problema de confidencialidad, no
un detalle de prolijidad.

Hasta la versión 1.0.7, "portable" solo quería decir que no hacía falta
instalador: la app igual escribía todo eso en `%APPDATA%` de esa máquina. Desde
1.0.7 el modo portable es portable de verdad.

### Si la carpeta es de solo lectura

Si el `.exe` está en un pendrive protegido contra escritura o en una carpeta
bloqueada por política de la empresa, la app **abre igual** y usa la carpeta de
usuario (avisa en la consola). Preferimos que funcione en medio de una visita al
cliente antes que se plante — pero entonces **sí queda rastro**: si te importa,
copiá el `.exe` a una carpeta donde puedas escribir antes de abrirlo.

---

## C · En el servidor del cliente (los datos no llegan a tu máquina)

El caso que ni A ni B resuelven: tu laptop de trabajo no te deja instalar nada
**y** los datos del cliente no pueden pasar por ella.

La app corre en un servidor, VM o contenedor **del cliente**; vos entrás solo
con el navegador. Al navegador viaja HTML, así que la base nunca sale de la
infraestructura del cliente. Al terminar, un comando borra todo.

```bash
cd servidor && docker compose up -d --build
docker compose exec mvsql python /app/preparar-propietario.py   # solo el dueño
```

Y desde tu laptop, un túnel y el navegador:

```bash
ssh -L 8791:127.0.0.1:8791 usuario@servidor-del-cliente
```

Hay también un camino sin Docker (`servidor/arrancar-sin-docker.sh`) para
servidores donde pedir Docker abre un ticket de tres semanas.

**Todo el detalle —qué queda dónde, cómo borrarlo, qué endurecer antes de
abrirlo a la red del cliente, y lo que este modo NO resuelve— está en
[MODO_SERVIDOR.md](MODO_SERVIDOR.md).** Vale leerlo entero antes de la primera
visita: la mitad de ese documento son las preguntas que hace el área de
seguridad del cliente.

---

## Si el instalador falla por espacio

Error real, en la máquina de un cliente:

```
Extrayendo: error escribiendo al archivo
C:\Users\Martin\AppData\Local\Temp\nsx4368.tmp\app-64.7z
```

Eso no es un problema del programa: es Windows quedándose sin lugar. Conviene
saber por qué aparece nombrando `C:` aunque la instalación vaya a otra unidad.

**Qué pasa.** Todo instalador de Windows se descomprime primero en la carpeta
temporal del perfil (`%TEMP%`), que vive en la unidad donde está el usuario —
casi siempre `C:` — y recién después copia los archivos a la carpeta que
elegiste. Esa carpeta temporal **no la puede mover el instalador**: en NSIS
`$TEMP` es una constante de solo lectura.

**Qué cambió en 1.0.9.** El instalador usaba la temporal dos veces: le volcaba
el paquete comprimido y además lo descomprimía entero ahí antes de copiarlo. En
total pedía unos **440 MB** libres en `C:`. Ahora descomprime directo a la
carpeta de instalación, así que pide unos **130 MB**. Y si ni eso hay, avisa
antes de empezar — en tu idioma, diciendo qué unidad, cuánto hay libre y cuánto
falta — en vez de fallar a mitad de camino con la ruta temporal en pantalla.

**Las tres salidas, de menor a mayor esfuerzo:**

1. **Liberar espacio en `C:`.** Con 200 MB alcanza. Papelera, `Descargas`, o
   Configuración → Sistema → Almacenamiento → Archivos temporales.
2. **Usar el `.zip` del programa.** En el mismo Release está
   `MV-SQL-NLP-<versión>.zip`: lo descomprimís en la unidad que quieras y
   ejecutás `MV SQL NLP.exe`. **No instala nada y no toca `C:`.** Es el mismo
   programa completo, sin acceso directo ni entrada en el menú Inicio.
3. **Apuntar `%TEMP%` a otra unidad.** Configuración → Sistema → Acerca de →
   Configuración avanzada del sistema → Variables de entorno → `TEMP` y `TMP`.
   Es lo más invasivo y lo último que probaría.

**Si `C:` tiene lugar de sobra y falla igual**, no es espacio: casi siempre es
el antivirus interrumpiendo la extracción. Agregá el instalador a las
excepciones, o usá el `.zip` del punto 2.

---

## Preguntas que aparecen siempre

**¿La portable o la del servidor tienen menos funciones?**
No. Es el mismo programa en las tres: mismos conectores, misma IA, mismo motor,
misma barrera de solo lectura.

**¿Puedo usar la misma licencia en las tres?**
Sí. La licencia es tuya, no de la máquina. En la portable va dentro de
`datos-mvsql\`; en el modo servidor, en el volumen del cliente.

**¿Y si el cliente quiere quedarse con el programa?**
Ahí compra su licencia y usa la forma A en su máquina. B y C son para cuando la
máquina no es de quien la usa.

**Mi laptop no me deja instalar NADA y el cliente no me da servidor ni VM.**
Entonces no hay solución técnica, ni de este producto ni de ningún otro: un
programa tiene que ejecutarse en algún lado. Eso se negocia antes de empezar el
proyecto. Ver la primera sección de [MODO_SERVIDOR.md](MODO_SERVIDOR.md), que
explica por qué pedir un contenedor en un servidor del cliente suele ser MÁS
fácil de conseguir que permiso para instalar en la laptop corporativa.

**¿Escribe algo en la base del cliente?**
Nunca. Toda conexión se abre en modo solo lectura y el motor rechaza cualquier
SQL que no empiece con `SELECT` o `WITH`. No hay camino de ejecución que haga
INSERT, UPDATE, DELETE ni DDL.
