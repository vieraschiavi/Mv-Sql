@echo off
setlocal EnableExtensions

REM ============================================================
REM  MV SQL NLP - Conector MCP para Claude Desktop
REM
REM  Conecta tu Claude Desktop (app de escritorio, con tu propia
REM  cuenta) DIRECTO a tu base de datos via MCP: le preguntas a
REM  Claude en lenguaje natural y consulta la base el solo.
REM
REM  Soporta: SQL Server / PostgreSQL / MySQL / SQLite
REM
REM  Basado en un setup validado en produccion:
REM   - Claude instalado por Microsoft Store (MSIX) virtualiza
REM     %%APPDATA%%\npm -> Node y el servidor MCP van a C:\MVSQL_MCP
REM     (ruta limpia, no virtualizada)
REM   - El config puede estar en Packages\Claude_*\LocalCache\
REM     Roaming\Claude (MSIX) o en %%APPDATA%%\Claude (instalador
REM     clasico): este script detecta cual corresponde
REM   - El servidor de SQL Server necesita MSSQL_CONNECTION_STRING
REM     (se incluyen ambos formatos por compatibilidad)
REM   - BAT 100 por ciento ASCII + CRLF
REM
REM  USO: doble clic y responde las preguntas. Se puede correr
REM  varias veces (agrega/actualiza conexiones sin pisar otras).
REM ============================================================

title MV SQL NLP - Conector MCP para Claude Desktop
color 0B

echo.
echo  ==========================================================
echo    MV SQL NLP - Conectar Claude Desktop a tu base (MCP)
echo  ==========================================================
echo.
echo  Claude va a poder consultar tu base directamente (solo
echo  lectura recomendada: crea un usuario de BD de solo SELECT).
echo.

REM --- RUTA BASE LIMPIA (no virtualizada por MSIX) ---
set "BASE=C:\MVSQL_MCP"
set "BASE_NODE=%BASE%\node"
set "BASE_MCP=%BASE%\mcp"
set "NODE_EXE=%BASE_NODE%\node.exe"
set "NPM_CLI=%BASE_NODE%\node_modules\npm\bin\npm-cli.js"
set "NODE_VERSION=v20.19.0"
set "NODE_URL=https://nodejs.org/dist/%NODE_VERSION%/node-%NODE_VERSION%-win-x64.zip"

REM =========================================================
REM  1) Elegir motor de base de datos
REM =========================================================
echo  Que motor de base de datos usas?
echo.
echo    1 = SQL Server
echo    2 = PostgreSQL
echo    3 = MySQL / MariaDB
echo    4 = SQLite (archivo .db)
echo.
set "MV_ENGINE="
set /p MV_ENGINE=  Opcion (1-4):
if "%MV_ENGINE%"=="1" set "MV_ENGINE=mssql"
if "%MV_ENGINE%"=="2" set "MV_ENGINE=postgres"
if "%MV_ENGINE%"=="3" set "MV_ENGINE=mysql"
if "%MV_ENGINE%"=="4" set "MV_ENGINE=sqlite"
if not "%MV_ENGINE%"=="mssql" if not "%MV_ENGINE%"=="postgres" if not "%MV_ENGINE%"=="mysql" if not "%MV_ENGINE%"=="sqlite" (
    echo  Opcion invalida. Corre el script de nuevo.
    pause
    exit /b 1
)

set /p MV_NAME=  Nombre para esta conexion (ej: ventas_sql):
if "%MV_NAME%"=="" set "MV_NAME=mi_base"

if "%MV_ENGINE%"=="sqlite" (
    set /p MV_SQLITE=  Ruta completa del archivo .db (ej: C:\datos\ventas.db):
) else (
    set /p MV_HOST=  Servidor / host (ej: 10.0.0.5 o localhost):
    set /p MV_PORT=  Puerto (Enter = default del motor):
    set /p MV_DB=  Nombre de la base:
    set /p MV_USER=  Usuario:
    set /p MV_PASS=  Password:
)

REM =========================================================
echo.
echo [1/5] Creando estructura %BASE% ...
if not exist "%BASE%"      mkdir "%BASE%"      2>nul
if not exist "%BASE_NODE%" mkdir "%BASE_NODE%" 2>nul
if not exist "%BASE_MCP%"  mkdir "%BASE_MCP%"  2>nul
if not exist "%BASE%" (
    echo  ERROR: No se pudo crear %BASE%
    pause
    exit /b 1
)
echo  OK

REM =========================================================
echo.
echo [2/5] Verificando Node.js ...
"%NODE_EXE%" --version >nul 2>&1
if not errorlevel 1 goto NODE_OK

REM Reusar un Node ya instalado en el sistema (>=18)
for /f "delims=" %%P in ('powershell -NoProfile -Command "(Get-Command node -EA SilentlyContinue).Source" 2^>nul') do (
    if exist "%%P" (
        for /f "delims=" %%D in ("%%P") do robocopy "%%~dpD." "%BASE_NODE%" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul 2>&1
    )
)
"%NODE_EXE%" --version >nul 2>&1
if not errorlevel 1 goto NODE_OK

REM Descargar Node portable
echo  Descargando Node.js %NODE_VERSION% (una sola vez)...
set "NODE_ZIP=%TEMP%\mvsql_node.zip"
del "%NODE_ZIP%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12,Tls13'; try{Invoke-WebRequest -Uri '%NODE_URL%' -OutFile '%NODE_ZIP%' -UseBasicParsing -TimeoutSec 180}catch{}" >nul 2>&1
if not exist "%NODE_ZIP%" (
    echo  ERROR: No se pudo descargar Node. Revisa tu conexion a internet.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive '%NODE_ZIP%' '%TEMP%\mvsql_node' -Force" >nul 2>&1
for /d %%D in ("%TEMP%\mvsql_node\node-*") do robocopy "%%D" "%BASE_NODE%" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul 2>&1
del "%NODE_ZIP%" >nul 2>&1
rd /s /q "%TEMP%\mvsql_node" >nul 2>&1
"%NODE_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: node.exe no responde
    pause
    exit /b 1
)

:NODE_OK
for /f %%v in ('"%NODE_EXE%" --version 2^>nul') do echo  OK Node: %%v

REM =========================================================
echo.
echo [3/5] Instalando servidor MCP para %MV_ENGINE% ...
set "MCP_PKG="
if "%MV_ENGINE%"=="mssql"    set "MCP_PKG=mssql-mcp-server"
if "%MV_ENGINE%"=="postgres" set "MCP_PKG=@modelcontextprotocol/server-postgres"
if "%MV_ENGINE%"=="mysql"    set "MCP_PKG=@benborla29/mcp-server-mysql"
if "%MV_ENGINE%"=="sqlite"   set "MCP_PKG=mcp-server-sqlite-npx"

"%NODE_EXE%" "%NPM_CLI%" install %MCP_PKG% --prefix "%BASE_MCP%" --no-save >nul 2>&1
powershell -NoProfile -Command "$p=Join-Path 'C:\MVSQL_MCP\mcp\node_modules' ($env:MCP_PKG -replace '/','\'); if(-not (Test-Path $p)){exit 1}" >nul 2>&1
if errorlevel 1 (
    echo  Reintento...
    timeout /t 4 /nobreak >nul
    "%NODE_EXE%" "%NPM_CLI%" install %MCP_PKG% --prefix "%BASE_MCP%" --no-save
)
echo  OK %MCP_PKG% instalado

REM =========================================================
echo.
echo [4/5] Escribiendo configuracion de Claude Desktop ...

REM El PowerShell:
REM  - localiza el config real (MSIX LocalCache o %%APPDATA%%\Claude)
REM  - hace backup
REM  - AGREGA/actualiza esta conexion sin pisar otros servidores MCP
REM  - resuelve el entry point real del paquete instalado
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$cfgDir=$null;" ^
  "Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Packages') -Directory -Filter 'Claude_*' -EA SilentlyContinue | ForEach-Object { $p=Join-Path $_.FullName 'LocalCache\Roaming\Claude'; if(Test-Path $p){$cfgDir=$p} };" ^
  "if(-not $cfgDir){ $p=Join-Path $env:APPDATA 'Claude'; if(Test-Path $p){$cfgDir=$p} }" ^
  "if(-not $cfgDir){ $cfgDir=Join-Path $env:APPDATA 'Claude'; New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null }" ^
  "$cfg=Join-Path $cfgDir 'claude_desktop_config.json';" ^
  "if(Test-Path $cfg){Copy-Item $cfg ($cfg+'.bak') -Force; try{$json=Get-Content $cfg -Raw | ConvertFrom-Json}catch{$json=$null}} else {$json=$null}" ^
  "if(-not $json){$json=[pscustomobject]@{}}" ^
  "if(-not ($json.PSObject.Properties.Name -contains 'mcpServers')){$json | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})}" ^
  "$node='C:\MVSQL_MCP\node\node.exe';" ^
  "$pkgDir=Join-Path 'C:\MVSQL_MCP\mcp\node_modules' ($env:MCP_PKG -replace '/','\');" ^
  "$pj=Get-Content (Join-Path $pkgDir 'package.json') -Raw | ConvertFrom-Json;" ^
  "$entry=$null; if($pj.bin){ if($pj.bin -is [string]){$entry=$pj.bin}else{$entry=($pj.bin.PSObject.Properties | Select-Object -First 1).Value} } if(-not $entry -and $pj.main){$entry=$pj.main}" ^
  "$mcpjs=Join-Path $pkgDir $entry;" ^
  "if(-not (Test-Path $mcpjs)){throw ('No se encontro el entry point: '+$mcpjs)}" ^
  "$eng=$env:MV_ENGINE; $srv=$null;" ^
  "if($eng -eq 'mssql'){ $port=if($env:MV_PORT){$env:MV_PORT}else{'1433'}; $cs='Server='+$env:MV_HOST+','+$port+';Database='+$env:MV_DB+';User Id='+$env:MV_USER+';Password='+$env:MV_PASS+';TrustServerCertificate=True;'; $srv=[pscustomobject]@{command=$node;args=@($mcpjs);env=[pscustomobject]@{MSSQL_CONNECTION_STRING=$cs;DB_SERVER=$env:MV_HOST;DB_DATABASE=$env:MV_DB;DB_USER=$env:MV_USER;DB_PASSWORD=$env:MV_PASS;DB_PORT=$port;DB_TRUST_SERVER_CERTIFICATE='true'}} }" ^
  "if($eng -eq 'postgres'){ $port=if($env:MV_PORT){$env:MV_PORT}else{'5432'}; $cs='postgresql://'+$env:MV_USER+':'+$env:MV_PASS+'@'+$env:MV_HOST+':'+$port+'/'+$env:MV_DB; $srv=[pscustomobject]@{command=$node;args=@($mcpjs,$cs)} }" ^
  "if($eng -eq 'mysql'){ $port=if($env:MV_PORT){$env:MV_PORT}else{'3306'}; $srv=[pscustomobject]@{command=$node;args=@($mcpjs);env=[pscustomobject]@{MYSQL_HOST=$env:MV_HOST;MYSQL_PORT=$port;MYSQL_USER=$env:MV_USER;MYSQL_PASS=$env:MV_PASS;MYSQL_DB=$env:MV_DB}} }" ^
  "if($eng -eq 'sqlite'){ $srv=[pscustomobject]@{command=$node;args=@($mcpjs,$env:MV_SQLITE)} }" ^
  "if($json.mcpServers.PSObject.Properties.Name -contains $env:MV_NAME){$json.mcpServers.PSObject.Properties.Remove($env:MV_NAME)}" ^
  "$json.mcpServers | Add-Member -NotePropertyName $env:MV_NAME -NotePropertyValue $srv;" ^
  "[System.IO.File]::WriteAllText($cfg,($json|ConvertTo-Json -Depth 10),[System.Text.UTF8Encoding]::new($false));" ^
  "Get-Content $cfg -Raw | ConvertFrom-Json | Out-Null;" ^
  "Write-Host ('CONFIG_OK '+$cfg)" > "%TEMP%\mvsql_mcp_result.txt" 2>&1

findstr /c:"CONFIG_OK" "%TEMP%\mvsql_mcp_result.txt" >nul
if errorlevel 1 (
    echo  ERROR: fallo escribiendo el config de Claude:
    type "%TEMP%\mvsql_mcp_result.txt"
    pause
    exit /b 1
)
for /f "tokens=2*" %%a in ('findstr /c:"CONFIG_OK" "%TEMP%\mvsql_mcp_result.txt"') do echo  OK Config: %%a %%b
del "%TEMP%\mvsql_mcp_result.txt" >nul 2>&1

REM =========================================================
echo.
echo [5/5] Reiniciando Claude Desktop ...
tasklist /FI "IMAGENAME eq Claude.exe" 2>nul | findstr /i "Claude.exe" >nul
if not errorlevel 1 (
    taskkill /F /IM Claude.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
)
set "CLAUDE_EXE="
if exist "%LOCALAPPDATA%\AnthropicClaude\claude.exe" set "CLAUDE_EXE=%LOCALAPPDATA%\AnthropicClaude\claude.exe"
if not defined CLAUDE_EXE (
    for /f "delims=" %%P in ('powershell -NoProfile -Command "Get-ChildItem $env:LOCALAPPDATA\Packages -Recurse -Filter Claude.exe -EA SilentlyContinue | Where-Object {$_.Length -gt 50MB} | Select-Object -First 1 -ExpandProperty FullName" 2^>nul') do set "CLAUDE_EXE=%%P"
)
if defined CLAUDE_EXE (
    start "" "%CLAUDE_EXE%"
    echo  OK Claude iniciado
) else (
    echo  AVISO: abre Claude manualmente desde el menu inicio
)

echo.
echo  ==========================================================
echo    LISTO. Conexion "%MV_NAME%" (%MV_ENGINE%) agregada.
echo  ==========================================================
echo    Espera 15 segundos con Claude abierto y proba:
echo    "que tablas tiene mi base %MV_NAME%?"
echo.
echo    Consejo de seguridad: usa un usuario de BD de solo
echo    lectura (solo SELECT) para esta conexion.
echo  ==========================================================
echo.
pause
exit /b 0
