# © 2026 Martín Viera. Todos los derechos reservados.

# MV SQL NLP — conversor a version propietario (detecta la instalacion sola)
# ============================================================================
# Metodologia portada de otro producto propio (MV Agendate IA): instalas el
# programa NORMAL, el mismo que baja cualquier cliente, y DESPUES corres este
# script UNA vez. El busca solo donde quedaron instalados los productos
# (registro de Windows, accesos directos, carpetas tipicas) y les escribe la
# licencia de propietario ahi -- sin que tengas que andar buscando la carpeta
# a mano ni copiar nada vos mismo.
#
# ESTE ARCHIVO ES LA PLANTILLA, sin licencia real adentro. Se versiona tal
# cual: el marcador @@LICENCIA_OWNER_JSON@@ no pasa el chequeo de abajo, asi
# que si alguien lo corre tal como esta en el repo, corta antes de escribir
# nada. La version CON la licencia real la genera
# tools/generar_conversor_owner.py, en tu maquina, y el resultado queda en
# owner/dist/ -- una carpeta que esta en .gitignore a proposito: si el .ps1
# con la licencia real llegara a subirse al repo publico, cualquiera que lo
# baje se convierte en "propietario" sin pagar nada.
#
# Que hace, en orden:
#
#   1) Busca donde quedo instalado el producto PYTHON (el que trae
#      INICIAR_MVSQL.bat + motor.py al lado). Ahi la carpeta SI varia segun
#      donde cada uno elija instalar o descomprimir, asi que hace falta
#      buscarla: registro de "Agregar o quitar programas" (lo escribe
#      installer/mvsql.nsi al instalar), accesos directos de escritorio y
#      menu inicio, y una busqueda acotada en carpetas tipicas. Si la
#      encuentra, escribe licencia_mvsql.json al lado del codigo -- que es
#      justo donde app-python/licencia.py la busca.
#
#   2) Busca la carpeta de datos del producto ELECTRON. Esa carpeta es FIJA
#      (depende de %APPDATA%, no de donde se instalo el .exe -- Electron
#      guarda ahi sin importar si elegiste Archivos de Programa u otra
#      carpeta), pero el nombre interno puede no ser exactamente
#      "MV SQL NLP" (Electron usa el campo interno del programa, no
#      necesariamente el nombre visible), asi que se busca por coincidencia
#      en vez de asumir el nombre exacto. Si la encuentra, escribe la misma
#      licencia ahi -- que es donde desktop/electron/services/licencia.cjs
#      la busca (app.getPath("userData")).
#
#   3) Si no encuentra ninguna de las dos instalaciones, NO rompe nada: avisa
#      y listo. Nunca escribe una licencia a mitad de camino ni en un lugar
#      que no pudo confirmar.
#
# No hace falta permisos de administrador: todo lo que toca (HKCU, %APPDATA%,
# carpetas del usuario) es del usuario actual.
# ============================================================================

$LicenciaOwner = '@@LICENCIA_OWNER_JSON@@'

if ($LicenciaOwner -notmatch '"vence"\s*:\s*"2099') {
  Write-Host ""
  Write-Host "Esta es la PLANTILLA, sin licencia real adentro." -ForegroundColor Red
  Write-Host "Generala con: python3 tools/generar_conversor_owner.py" -ForegroundColor Yellow
  Write-Host ""
  Read-Host "Presiona ENTER para salir"
  exit 1
}

# ---------------------------------------------------------------------------
# Deteccion del producto Python
# ---------------------------------------------------------------------------
function Buscar-CarpetaPython {
  $candidatos = New-Object System.Collections.Generic.List[string]

  # 1) Registro de "Agregar o quitar programas". Dos claves posibles: la
  #    normal y la de una eventual build owner ya compilada por CI (no
  #    hace nada si no existe, Get-ItemProperty no tira si falta la clave).
  foreach ($clave in @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MVSQLNLP',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MVSQLNLP_OWNER'
  )) {
    $item = Get-ItemProperty -LiteralPath $clave -ErrorAction SilentlyContinue
    if ($item -and $item.InstallLocation) { $candidatos.Add($item.InstallLocation) }
  }

  # 2) Accesos directos: el instalador crea uno en el escritorio y otro en
  #    el menu inicio (dentro de una subcarpeta que el usuario elige al
  #    instalar, por eso la busqueda del menu inicio es recursiva).
  $shell = New-Object -ComObject WScript.Shell
  $lnks = New-Object System.Collections.Generic.List[string]
  $lnkEscritorio = Join-Path ([Environment]::GetFolderPath('Desktop')) 'MV SQL NLP.lnk'
  if (Test-Path -LiteralPath $lnkEscritorio) { $lnks.Add($lnkEscritorio) }
  $menuInicio = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
  if (Test-Path -LiteralPath $menuInicio) {
    Get-ChildItem -Path $menuInicio -Filter 'MV SQL NLP.lnk' -Recurse -Depth 2 -ErrorAction SilentlyContinue |
      ForEach-Object { $lnks.Add($_.FullName) }
  }
  foreach ($lnk in $lnks) {
    $destino = $shell.CreateShortcut($lnk).TargetPath
    if ($destino) { $candidatos.Add((Split-Path -Parent $destino)) }
  }

  # 3) Busqueda acotada en carpetas tipicas -- cubre el caso del .zip
  #    portable, que no crea ni registro ni accesos directos.
  $raices = @(
    [Environment]::GetFolderPath('Desktop'),
    [Environment]::GetFolderPath('MyDocuments'),
    (Join-Path $env:USERPROFILE 'Downloads'),
    $env:USERPROFILE
  )
  foreach ($raiz in $raices) {
    if (-not (Test-Path -LiteralPath $raiz)) { continue }
    foreach ($patron in @('MV-SQL-NLP*', 'MV SQL NLP*', 'mvsql-nlp*')) {
      Get-ChildItem -Path $raiz -Directory -Filter $patron -Recurse -Depth 2 -ErrorAction SilentlyContinue |
        ForEach-Object { $candidatos.Add($_.FullName) }
    }
  }
  foreach ($unidad in (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue)) {
    $raizUnidad = $unidad.Root
    if (-not (Test-Path -LiteralPath $raizUnidad)) { continue }
    foreach ($patron in @('MV-SQL-NLP*', 'MV SQL NLP*')) {
      Get-ChildItem -Path $raizUnidad -Directory -Filter $patron -ErrorAction SilentlyContinue |
        ForEach-Object { $candidatos.Add($_.FullName) }
    }
  }

  # Validacion: no alcanza con que la carpeta EXISTA, tiene que ser una
  # instalacion de verdad -- se prueba con dos archivos propios del
  # producto, no uno solo, para no confundir una carpeta de descargas
  # cualquiera con la instalacion real.
  $vistos = New-Object System.Collections.Generic.HashSet[string]
  foreach ($c in $candidatos) {
    if (-not $c -or -not (Test-Path -LiteralPath $c)) { continue }
    $resuelto = Resolve-Path -LiteralPath $c -ErrorAction SilentlyContinue
    if (-not $resuelto) { continue }
    $full = $resuelto.Path
    if ($vistos.Contains($full)) { continue }
    [void]$vistos.Add($full)
    if ((Test-Path (Join-Path $full 'INICIAR_MVSQL.bat')) -and (Test-Path (Join-Path $full 'motor.py'))) {
      return $full
    }
  }
  return $null
}

# ---------------------------------------------------------------------------
# Deteccion de la carpeta de datos de Electron
# ---------------------------------------------------------------------------
function Buscar-CarpetaDatosElectron {
  if (-not (Test-Path -LiteralPath $env:APPDATA)) { return $null }
  Get-ChildItem -Path $env:APPDATA -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $normalizado = ($_.Name -replace '[\s_-]', '').ToLowerInvariant()
    if ($normalizado -eq 'mvsqlnlp') { $_.FullName }
  } | Select-Object -First 1
}

# ---------------------------------------------------------------------------
# Accion
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "== MV SQL NLP -- conversion a version propietario ==" -ForegroundColor Cyan
Write-Host ""

$encontroAlgo = $false

$carpetaPython = Buscar-CarpetaPython
if ($carpetaPython) {
  $destino = Join-Path $carpetaPython 'licencia_mvsql.json'
  Set-Content -LiteralPath $destino -Encoding utf8 -Value $LicenciaOwner -NoNewline
  # Se relee para confirmar que la escritura tomo antes de decir "listo" --
  # si el antivirus la bloqueo en silencio, mejor avisar que mentir.
  $releido = Get-Content -LiteralPath $destino -Raw -ErrorAction SilentlyContinue
  if ($releido -and ($releido -match '"vence"')) {
    Write-Host "OK   Python   -> $destino" -ForegroundColor Green
    $encontroAlgo = $true
  } else {
    Write-Host "FALLO Python  -> no se pudo confirmar la escritura en $destino" -ForegroundColor Red
  }
} else {
  Write-Host "--   Python   no se encontro una instalacion" -ForegroundColor DarkGray
}

$carpetaElectron = Buscar-CarpetaDatosElectron
if ($carpetaElectron) {
  $destino = Join-Path $carpetaElectron 'licencia_mvsql.json'
  Set-Content -LiteralPath $destino -Encoding utf8 -Value $LicenciaOwner -NoNewline
  $releido = Get-Content -LiteralPath $destino -Raw -ErrorAction SilentlyContinue
  if ($releido -and ($releido -match '"vence"')) {
    Write-Host "OK   Electron -> $destino" -ForegroundColor Green
    $encontroAlgo = $true
  } else {
    Write-Host "FALLO Electron -> no se pudo confirmar la escritura en $destino" -ForegroundColor Red
  }
} else {
  Write-Host "--   Electron no se encontro (¿lo abriste al menos una vez?)" -ForegroundColor DarkGray
}

Write-Host ""
if ($encontroAlgo) {
  Write-Host "Listo. Cerra y volve a abrir el/los programa(s) que encontro arriba." -ForegroundColor Cyan
} else {
  Write-Host "No se encontro ninguna instalacion." -ForegroundColor Yellow
  Write-Host "Instala el producto (el .exe de Electron o el de Python) y abrilo al menos" -ForegroundColor Yellow
  Write-Host "una vez -- despues volve a correr este script." -ForegroundColor Yellow
}
Write-Host ""
Read-Host "Presiona ENTER para salir"
