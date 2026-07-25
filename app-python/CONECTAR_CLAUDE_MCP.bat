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

REM =========================================================
REM  0) Idioma. Si el launcher ya lo pregunto, se reusa.
REM     Los textos que se muestran DENTRO de un bloque if(...)
REM     no llevan parentesis a proposito: sin expansion
REM     retardada, un ')' del valor cerraria el bloque.
REM     No se activa EnableDelayedExpansion para que un password
REM     con '!' siga funcionando.
REM =========================================================
set "MVSQL_LANG="
if exist "%~dp0.idioma" set /p MVSQL_LANG=<"%~dp0.idioma"
if "%MVSQL_LANG%"=="es" goto LANG_OK
if "%MVSQL_LANG%"=="en" goto LANG_OK
if "%MVSQL_LANG%"=="pt" goto LANG_OK
echo.
echo    [1] Espanol     [2] English     [3] Portugues
echo.
choice /c 123 /n /m "  Idioma / Language / Idioma: "
if errorlevel 3 goto LANG_PT
if errorlevel 2 goto LANG_EN
set "MVSQL_LANG=es"
goto LANG_SAVE
:LANG_PT
set "MVSQL_LANG=pt"
goto LANG_SAVE
:LANG_EN
set "MVSQL_LANG=en"
:LANG_SAVE
echo %MVSQL_LANG%> "%~dp0.idioma"

:LANG_OK
if "%MVSQL_LANG%"=="en" goto TXT_EN
if "%MVSQL_LANG%"=="pt" goto TXT_PT

:TXT_ES
set "C_TIT=MV SQL NLP - Conectar Claude Desktop a tu base (MCP)"
set "C_SUB1=Claude va a poder consultar tu base directamente (solo"
set "C_SUB2=lectura recomendada: crea un usuario de BD de solo SELECT)."
set "C_MOTOR=Que motor de base de datos usas?"
set "C_OPCION=  Opcion (1-4):"
set "C_INVALIDA= Opcion invalida. Corre el script de nuevo."
set "C_NOMBRE=  Nombre para esta conexion, por ejemplo ventas_sql:"
set "C_RUTA=  Ruta completa del archivo .db, por ejemplo C:\datos\ventas.db:"
set "C_HOST=  Servidor / host, por ejemplo 10.0.0.5 o localhost:"
set "C_PUERTO=  Puerto, Enter para el valor por defecto:"
set "C_BASE=  Nombre de la base:"
set "C_USUARIO=  Usuario:"
set "C_PASS=  Password:"
set "C_P1=[1/5] Creando estructura"
set "C_E_DIR= ERROR: No se pudo crear"
set "C_P2=[2/5] Verificando Node.js ..."
set "C_BAJANDO= Descargando Node.js"
set "C_UNAVEZ=una sola vez ..."
set "C_E_NODE= ERROR: No se pudo descargar Node. Revisa tu conexion a internet."
set "C_E_NODE2= ERROR: node.exe no responde"
set "C_P3=[3/5] Instalando servidor MCP para"
set "C_REINTENTO= Reintento..."
set "C_INSTALADO=instalado"
set "C_P4=[4/5] Escribiendo configuracion de Claude Desktop ..."
set "C_E_CFG= ERROR: fallo escribiendo el config de Claude:"
set "C_P5=[5/5] Reiniciando Claude Desktop ..."
set "C_CLAUDE_OK= OK Claude iniciado"
set "C_CLAUDE_NO= AVISO: abre Claude manualmente desde el menu inicio"
set "C_LISTO=LISTO. Conexion agregada:"
set "C_ESPERA=Espera 15 segundos con Claude abierto y proba:"
set "C_PRUEBA=que tablas tiene mi base"
set "C_SEGURIDAD1=Consejo de seguridad: usa un usuario de BD de solo"
set "C_SEGURIDAD2=lectura (solo SELECT) para esta conexion."
goto TXT_FIN

:TXT_EN
set "C_TIT=MV SQL NLP - Connect Claude Desktop to your database (MCP)"
set "C_SUB1=Claude will be able to query your database directly (a"
set "C_SUB2=read-only DB user is strongly recommended: SELECT only)."
set "C_MOTOR=Which database engine do you use?"
set "C_OPCION=  Option (1-4):"
set "C_INVALIDA= Invalid option. Run the script again."
set "C_NOMBRE=  Name for this connection, for example sales_sql:"
set "C_RUTA=  Full path to the .db file, for example C:\data\sales.db:"
set "C_HOST=  Server / host, for example 10.0.0.5 or localhost:"
set "C_PUERTO=  Port, press Enter for the default:"
set "C_BASE=  Database name:"
set "C_USUARIO=  User:"
set "C_PASS=  Password:"
set "C_P1=[1/5] Creating folder"
set "C_E_DIR= ERROR: Could not create"
set "C_P2=[2/5] Checking Node.js ..."
set "C_BAJANDO= Downloading Node.js"
set "C_UNAVEZ=one time only ..."
set "C_E_NODE= ERROR: Could not download Node. Check your internet connection."
set "C_E_NODE2= ERROR: node.exe is not responding"
set "C_P3=[3/5] Installing the MCP server for"
set "C_REINTENTO= Retrying..."
set "C_INSTALADO=installed"
set "C_P4=[4/5] Writing the Claude Desktop configuration ..."
set "C_E_CFG= ERROR: could not write the Claude config:"
set "C_P5=[5/5] Restarting Claude Desktop ..."
set "C_CLAUDE_OK= OK Claude started"
set "C_CLAUDE_NO= NOTE: open Claude manually from the Start Menu"
set "C_LISTO=DONE. Connection added:"
set "C_ESPERA=Wait 15 seconds with Claude open and try:"
set "C_PRUEBA=what tables are in my database"
set "C_SEGURIDAD1=Security tip: use a read-only database user"
set "C_SEGURIDAD2=(SELECT only) for this connection."
goto TXT_FIN

:TXT_PT
set "C_TIT=MV SQL NLP - Conectar o Claude Desktop ao seu banco (MCP)"
set "C_SUB1=O Claude vai poder consultar seu banco direto (o"
set "C_SUB2=recomendado e criar um usuario de banco so de SELECT)."
set "C_MOTOR=Qual motor de banco de dados voce usa?"
set "C_OPCION=  Opcao (1-4):"
set "C_INVALIDA= Opcao invalida. Rode o script de novo."
set "C_NOMBRE=  Nome para esta conexao, por exemplo vendas_sql:"
set "C_RUTA=  Caminho completo do arquivo .db, por exemplo C:\dados\vendas.db:"
set "C_HOST=  Servidor / host, por exemplo 10.0.0.5 ou localhost:"
set "C_PUERTO=  Porta, Enter para o valor padrao:"
set "C_BASE=  Nome do banco:"
set "C_USUARIO=  Usuario:"
set "C_PASS=  Senha:"
set "C_P1=[1/5] Criando a estrutura"
set "C_E_DIR= ERRO: Nao foi possivel criar"
set "C_P2=[2/5] Verificando o Node.js ..."
set "C_BAJANDO= Baixando o Node.js"
set "C_UNAVEZ=uma unica vez ..."
set "C_E_NODE= ERRO: Nao foi possivel baixar o Node. Verifique sua conexao."
set "C_E_NODE2= ERRO: node.exe nao responde"
set "C_P3=[3/5] Instalando o servidor MCP para"
set "C_REINTENTO= Tentando de novo..."
set "C_INSTALADO=instalado"
set "C_P4=[4/5] Escrevendo a configuracao do Claude Desktop ..."
set "C_E_CFG= ERRO: falha ao escrever o config do Claude:"
set "C_P5=[5/5] Reiniciando o Claude Desktop ..."
set "C_CLAUDE_OK= OK Claude iniciado"
set "C_CLAUDE_NO= AVISO: abra o Claude manualmente pelo Menu Iniciar"
set "C_LISTO=PRONTO. Conexao adicionada:"
set "C_ESPERA=Espere 15 segundos com o Claude aberto e teste:"
set "C_PRUEBA=quais tabelas tem no meu banco"
set "C_SEGURIDAD1=Dica de seguranca: use um usuario de banco somente"
set "C_SEGURIDAD2=leitura (so SELECT) para esta conexao."
goto TXT_FIN

:TXT_FIN

echo.
echo  ==========================================================
echo    %C_TIT%
echo  ==========================================================
echo.
echo  %C_SUB1%
echo  %C_SUB2%
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
echo  %C_MOTOR%
echo.
echo    1 = SQL Server
echo    2 = PostgreSQL
echo    3 = MySQL / MariaDB
echo    4 = SQLite (archivo .db)
echo.
set "MV_ENGINE="
set /p MV_ENGINE=%C_OPCION%
if "%MV_ENGINE%"=="1" set "MV_ENGINE=mssql"
if "%MV_ENGINE%"=="2" set "MV_ENGINE=postgres"
if "%MV_ENGINE%"=="3" set "MV_ENGINE=mysql"
if "%MV_ENGINE%"=="4" set "MV_ENGINE=sqlite"
if not "%MV_ENGINE%"=="mssql" if not "%MV_ENGINE%"=="postgres" if not "%MV_ENGINE%"=="mysql" if not "%MV_ENGINE%"=="sqlite" (
    echo %C_INVALIDA%
    pause
    exit /b 1
)

set /p MV_NAME=%C_NOMBRE%
if "%MV_NAME%"=="" set "MV_NAME=mi_base"

if "%MV_ENGINE%"=="sqlite" (
    set /p MV_SQLITE=%C_RUTA%
) else (
    set /p MV_HOST=%C_HOST%
    set /p MV_PORT=%C_PUERTO%
    set /p MV_DB=%C_BASE%
    set /p MV_USER=%C_USUARIO%
    set /p MV_PASS=%C_PASS%
)

REM =========================================================
echo.
echo %C_P1% %BASE% ...
if not exist "%BASE%"      mkdir "%BASE%"      2>nul
if not exist "%BASE_NODE%" mkdir "%BASE_NODE%" 2>nul
if not exist "%BASE_MCP%"  mkdir "%BASE_MCP%"  2>nul
if not exist "%BASE%" (
    echo %C_E_DIR% %BASE%
    pause
    exit /b 1
)
echo  OK

REM =========================================================
echo.
echo %C_P2%
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
echo %C_BAJANDO% %NODE_VERSION% - %C_UNAVEZ%
set "NODE_ZIP=%TEMP%\mvsql_node.zip"
del "%NODE_ZIP%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12,Tls13'; try{Invoke-WebRequest -Uri '%NODE_URL%' -OutFile '%NODE_ZIP%' -UseBasicParsing -TimeoutSec 180}catch{}" >nul 2>&1
if not exist "%NODE_ZIP%" (
    echo %C_E_NODE%
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive '%NODE_ZIP%' '%TEMP%\mvsql_node' -Force" >nul 2>&1
for /d %%D in ("%TEMP%\mvsql_node\node-*") do robocopy "%%D" "%BASE_NODE%" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul 2>&1
del "%NODE_ZIP%" >nul 2>&1
rd /s /q "%TEMP%\mvsql_node" >nul 2>&1
"%NODE_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo %C_E_NODE2%
    pause
    exit /b 1
)

:NODE_OK
for /f %%v in ('"%NODE_EXE%" --version 2^>nul') do echo  OK Node: %%v

REM =========================================================
echo.
echo %C_P3% %MV_ENGINE% ...
set "MCP_PKG="
if "%MV_ENGINE%"=="mssql"    set "MCP_PKG=mssql-mcp-server"
if "%MV_ENGINE%"=="postgres" set "MCP_PKG=@modelcontextprotocol/server-postgres"
if "%MV_ENGINE%"=="mysql"    set "MCP_PKG=@benborla29/mcp-server-mysql"
if "%MV_ENGINE%"=="sqlite"   set "MCP_PKG=mcp-server-sqlite-npx"

"%NODE_EXE%" "%NPM_CLI%" install %MCP_PKG% --prefix "%BASE_MCP%" --no-save >nul 2>&1
powershell -NoProfile -Command "$p=Join-Path 'C:\MVSQL_MCP\mcp\node_modules' ($env:MCP_PKG -replace '/','\'); if(-not (Test-Path $p)){exit 1}" >nul 2>&1
if errorlevel 1 (
    echo %C_REINTENTO%
    timeout /t 4 /nobreak >nul
    "%NODE_EXE%" "%NPM_CLI%" install %MCP_PKG% --prefix "%BASE_MCP%" --no-save
)
echo  OK %MCP_PKG% %C_INSTALADO%

REM =========================================================
echo.
echo %C_P4%

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
    echo %C_E_CFG%
    type "%TEMP%\mvsql_mcp_result.txt"
    pause
    exit /b 1
)
for /f "tokens=2*" %%a in ('findstr /c:"CONFIG_OK" "%TEMP%\mvsql_mcp_result.txt"') do echo  OK Config: %%a %%b
del "%TEMP%\mvsql_mcp_result.txt" >nul 2>&1

REM =========================================================
echo.
echo %C_P5%
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
    echo %C_CLAUDE_OK%
) else (
    echo %C_CLAUDE_NO%
)

echo.
echo  ==========================================================
echo    %C_LISTO% %MV_NAME% - %MV_ENGINE%
echo  ==========================================================
echo    %C_ESPERA%
echo    %C_PRUEBA% %MV_NAME%
echo.
echo    %C_SEGURIDAD1%
echo    %C_SEGURIDAD2%
echo  ==========================================================
echo.
pause
exit /b 0
