# © 2026 Martín Viera. Todos los derechos reservados.

# Conversor a versión propietario — cómo se usa

Metodología portada de otro producto propio (MV Agendate IA): en vez de compilar
un `.exe`/`.zip` "owner" aparte (que sigue existiendo como alternativa — ver
`.github/workflows/build-desktop.yml`), instalás el producto **normal**, el
mismo que baja cualquier cliente, y después corrés **un script que detecta
solo** dónde quedó instalado y le escribe la licencia de por vida ahí. No hace
falta saber la carpeta, ni copiar nada a mano, ni permisos de administrador.

## Paso 1 — generar el conversor CON la licencia real (una sola vez, en tu máquina)

```
python3 tools/generar_conversor_owner.py
```

Esto deja en `owner/dist/` (que está en `.gitignore` — **nunca se commitea**):

- `convertir-a-version-dueno.ps1` — el motor de detección, con la licencia real adentro.
- `Convertir-a-version-dueno.bat` — el punto de entrada (doble clic).

`owner/plantilla-convertir-a-dueno.ps1`, la que SÍ está en el repo, no tiene
licencia real — tiene el marcador `@@LICENCIA_OWNER_JSON@@`. Si alguien la baja
del repo público y la corre tal cual, el propio script la rechaza antes de
escribir nada (ver el chequeo al principio del archivo).

## Paso 2 — instalar el producto normal

Cualquiera de los dos (o los dos):

- **Electron**: `MV-SQL-NLP-App-Setup.exe` o el portable, igual que un cliente.
- **Python**: `MV-SQL-NLP-Setup.exe` (NSIS) o el `.zip` autoinstalable (`INICIAR_MVSQL.bat`).

Abrilo al menos una vez (para Electron: así se crea la carpeta de datos que el
conversor busca después).

## Paso 3 — correr el conversor

Doble clic en `Convertir-a-version-dueno.bat` (desde `owner/dist/`, o
copiado a donde quieras — no depende de la ubicación). Busca:

- La instalación **Python**: registro de "Agregar o quitar programas" (lo
  escribe `installer/mvsql.nsi`), accesos directos de escritorio/menú inicio, y
  una búsqueda acotada en Escritorio/Documentos/Descargas/carpeta de usuario y
  raíces de disco. Valida cada candidato comprobando que tenga
  `INICIAR_MVSQL.bat` + `motor.py` — no alcanza con que la carpeta exista.
- La instalación **Electron**: la carpeta de datos (`%APPDATA%`), que es fija
  sin importar dónde se instaló el `.exe`. Busca por nombre normalizado (sin
  espacios/guiones) porque el nombre interno del programa puede no coincidir
  letra por letra con el visible.

Si encuentra una o las dos, escribe `licencia_mvsql.json` en cada una y lo
confirma releyendo el archivo (no dice "listo" si la escritura no se pudo
verificar). Si no encuentra ninguna, avisa y no toca nada.

## Por qué el `.ps1` con la licencia real no se commitea

`_licencia_vigente()`/`vigente()`/`_licencia_vigente` (Python, Electron) sólo
validan la fecha `vence` del lado del cliente — es el mismo mecanismo que usa
una licencia comprada de verdad (`web/api/download.js`), no uno nuevo. Eso
significa que **el contenido del archivo generado, si se filtra, es
suficiente para que cualquiera se dé acceso perpetuo sin pagar** — igual que
pasaría si se filtrara `licencia_owner.json` (el mecanismo viejo) o el
`.exe`/`.zip` owner ya compilados. La protección no es criptográfica: es no
distribuirlo. `owner/dist/` está en `.gitignore` por esa razón exacta.

## Nota de esta implementación

El script `.ps1` no se pudo ejecutar ni probar en este entorno (Linux, sin
PowerShell) — se escribió con cuidado siguiendo la sintaxis de PowerShell 5.1+
y el mismo patrón que ya funciona en producción en MV Agendate IA, pero
**probalo en Windows antes de confiar en él** para tu instalación real.
