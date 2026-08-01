@echo off
setlocal EnableDelayedExpansion
title MV SQL NLP
color 0B

cd /d "%~dp0"

:: ======================================================================
:: IMPORTANTE PARA QUIEN EDITE ESTE ARCHIVO
:: Solo ASCII y saltos de linea CRLF. Un acento o un caracter de dibujo
:: hace que cmd.exe cierre la ventana al instante y el cliente ve el
:: programa "abrir y cerrar" sin ningun mensaje.
:: ======================================================================

:: -- 0. Idioma (se pregunta una sola vez y queda guardado) --------------
set "MVSQL_LANG="
if exist ".idioma" set /p MVSQL_LANG=<".idioma"
if "%MVSQL_LANG%"=="es" goto :lang_ok
if "%MVSQL_LANG%"=="en" goto :lang_ok
if "%MVSQL_LANG%"=="pt" goto :lang_ok

echo.
echo   ================================================================
echo     MV SQL NLP
echo   ================================================================
echo.
echo     [1] Espanol     [2] English     [3] Portugues
echo.
choice /c 123 /n /m "  Idioma / Language / Idioma: "
if errorlevel 3 ( set "MVSQL_LANG=pt" & goto :lang_guardar )
if errorlevel 2 ( set "MVSQL_LANG=en" & goto :lang_guardar )
set "MVSQL_LANG=es"

:lang_guardar
echo %MVSQL_LANG%> ".idioma"

:lang_ok
if "%MVSQL_LANG%"=="en" goto :textos_en
if "%MVSQL_LANG%"=="pt" goto :textos_pt

:textos_es
set "M_LEMA=Tu base de datos, en tu idioma"
set "M_NOPY=[X] No se encontro Python instalado."
set "M_BAJAR=Descargalo gratis de https://www.python.org/downloads/"
set "M_PATH=IMPORTANTE: al instalar, marca Add Python to PATH."
set "M_TECLA=Presiona una tecla para abrir la pagina de descarga..."
set "M_PY=Python detectado:"
set "M_VENV_NEW=Creando entorno virtual aislado (solo la primera vez)..."
set "M_VENV_OK=Entorno virtual OK"
set "M_VENV_ERR=[X] Fallo creando .venv"
set "M_DEPS=Instalando dependencias (2-5 min la primera vez)..."
set "M_DEPS_OK=Dependencias OK"
set "M_DEPS_ERR=[X] Fallo instalando dependencias."
set "M_EXTRAS=Instalando extras opcionales (no son necesarios para usar la app)..."
set "M_EXTRAS_NO=[*] Los extras opcionales no se instalaron. La app funciona igual."
set "M_DISCO_POCO=[X] No hay lugar suficiente en el disco."
set "M_DISCO_LIBRE=Libre ahora:"
set "M_DISCO_NEC=Hace falta al menos: 1.5 GB"
set "M_DISCO_COMO=Libera espacio (Configuracion ^> Sistema ^> Almacenamiento) y volve a ejecutar."
set "M_E_DISCO=Se lleno el disco durante la instalacion."
set "M_E_RED=No se pudo conectar para descargar. Revisa tu conexion o el proxy/firewall."
set "M_E_PERM=Windows bloqueo la escritura. Proba mover la carpeta fuera de Archivos de programa,"
set "M_E_PERM2=o ejecutar como administrador."
set "M_E_PYVER=Tu version de Python no es compatible con alguna libreria."
set "M_E_OTRO=Causa no reconocida. El detalle completo quedo en:"
set "M_LOG=Detalle tecnico:"
set "M_DEMO=Generando base de datos demo..."
set "M_DEMO_OK=Base demo OK"
set "M_DEMO_ERR=[*] No se pudo generar la demo (podes conectar tu propia base)"
set "M_ACC_PREG=  Crear acceso directo en Escritorio y Menu Inicio? [S/N]: "
set "M_ACC_SI=Accesos directos creados: Escritorio y Menu Inicio"
set "M_ACC_ONE=Accesos creados (si no ves el del Escritorio, tu Escritorio"
set "M_ACC_ONE2=puede estar en OneDrive - busca MV SQL NLP en el Menu Inicio)"
set "M_ACC_NO=Sin accesos directos (no se vuelve a preguntar)"
set "M_ACC_OK=Accesos directos OK"
set "M_INICIA=Iniciando MV SQL NLP en"
set "M_ABRE=La app se abre sola en tu navegador."
set "M_MANUAL=Si se abre otra pagina distinta, entra manualmente a:"
set "M_CERRAR=Para cerrarla: Ctrl+C o cerra esta ventana."
set "M_FIN=La app se cerro. Presiona una tecla para salir..."
goto :inicio

:textos_en
set "M_LEMA=Your database, in your own words"
set "M_NOPY=[X] Python is not installed."
set "M_BAJAR=Download it free from https://www.python.org/downloads/"
set "M_PATH=IMPORTANT: while installing, tick Add Python to PATH."
set "M_TECLA=Press any key to open the download page..."
set "M_PY=Python found:"
set "M_VENV_NEW=Creating an isolated virtual environment (first run only)..."
set "M_VENV_OK=Virtual environment OK"
set "M_VENV_ERR=[X] Could not create .venv"
set "M_DEPS=Installing dependencies (2-5 min on the first run)..."
set "M_DEPS_OK=Dependencies OK"
set "M_DEPS_ERR=[X] Could not install dependencies."
set "M_EXTRAS=Installing optional extras (not required to use the app)..."
set "M_EXTRAS_NO=[*] The optional extras were not installed. The app works anyway."
set "M_DISCO_POCO=[X] Not enough free disk space."
set "M_DISCO_LIBRE=Free right now:"
set "M_DISCO_NEC=At least needed: 1.5 GB"
set "M_DISCO_COMO=Free up space (Settings ^> System ^> Storage) and run this again."
set "M_E_DISCO=The disk filled up during the installation."
set "M_E_RED=Could not connect to download. Check your connection or proxy/firewall."
set "M_E_PERM=Windows blocked the write. Try moving the folder out of Program Files,"
set "M_E_PERM2=or running as administrator."
set "M_E_PYVER=Your Python version is not compatible with one of the libraries."
set "M_E_OTRO=Cause not recognised. The full detail was saved to:"
set "M_LOG=Technical detail:"
set "M_DEMO=Generating the demo database..."
set "M_DEMO_OK=Demo database OK"
set "M_DEMO_ERR=[*] Could not generate the demo (you can connect your own database)"
set "M_ACC_PREG=  Create a shortcut on the Desktop and Start Menu? [Y/N]: "
set "M_ACC_SI=Shortcuts created: Desktop and Start Menu"
set "M_ACC_ONE=Shortcuts created (if you cannot see the Desktop one, your"
set "M_ACC_ONE2=Desktop may be in OneDrive - look for MV SQL NLP in the Start Menu)"
set "M_ACC_NO=No shortcuts (you will not be asked again)"
set "M_ACC_OK=Shortcuts OK"
set "M_INICIA=Starting MV SQL NLP at"
set "M_ABRE=The app opens in your browser on its own."
set "M_MANUAL=If a different page opens, go manually to:"
set "M_CERRAR=To close it: Ctrl+C or close this window."
set "M_FIN=The app was closed. Press any key to exit..."
goto :inicio

:textos_pt
set "M_LEMA=Seu banco de dados, no seu idioma"
set "M_NOPY=[X] Python nao foi encontrado."
set "M_BAJAR=Baixe de graca em https://www.python.org/downloads/"
set "M_PATH=IMPORTANTE: ao instalar, marque Add Python to PATH."
set "M_TECLA=Pressione uma tecla para abrir a pagina de download..."
set "M_PY=Python encontrado:"
set "M_VENV_NEW=Criando ambiente virtual isolado (so na primeira vez)..."
set "M_VENV_OK=Ambiente virtual OK"
set "M_VENV_ERR=[X] Falha ao criar o .venv"
set "M_DEPS=Instalando dependencias (2-5 min na primeira vez)..."
set "M_DEPS_OK=Dependencias OK"
set "M_DEPS_ERR=[X] Falha ao instalar dependencias."
set "M_EXTRAS=Instalando extras opcionais (nao sao necessarios para usar o app)..."
set "M_EXTRAS_NO=[*] Os extras opcionais nao foram instalados. O app funciona do mesmo jeito."
set "M_DISCO_POCO=[X] Nao ha espaco suficiente em disco."
set "M_DISCO_LIBRE=Livre agora:"
set "M_DISCO_NEC=Minimo necessario: 1.5 GB"
set "M_DISCO_COMO=Libere espaco (Configuracoes ^> Sistema ^> Armazenamento) e execute de novo."
set "M_E_DISCO=O disco encheu durante a instalacao."
set "M_E_RED=Nao foi possivel conectar para baixar. Verifique a conexao ou o proxy/firewall."
set "M_E_PERM=O Windows bloqueou a escrita. Tente mover a pasta para fora de Arquivos de Programas,"
set "M_E_PERM2=ou executar como administrador."
set "M_E_PYVER=Sua versao do Python nao e compativel com alguma biblioteca."
set "M_E_OTRO=Causa nao reconhecida. O detalhe completo ficou em:"
set "M_LOG=Detalhe tecnico:"
set "M_DEMO=Gerando o banco de dados de demonstracao..."
set "M_DEMO_OK=Banco de demonstracao OK"
set "M_DEMO_ERR=[*] Nao foi possivel gerar a demo (voce pode conectar seu proprio banco)"
set "M_ACC_PREG=  Criar atalho na Area de Trabalho e no Menu Iniciar? [S/N]: "
set "M_ACC_SI=Atalhos criados: Area de Trabalho e Menu Iniciar"
set "M_ACC_ONE=Atalhos criados (se nao vir o da Area de Trabalho, ela pode"
set "M_ACC_ONE2=estar no OneDrive - procure MV SQL NLP no Menu Iniciar)"
set "M_ACC_NO=Sem atalhos (nao sera perguntado de novo)"
set "M_ACC_OK=Atalhos OK"
set "M_INICIA=Iniciando o MV SQL NLP em"
set "M_ABRE=O app abre sozinho no seu navegador."
set "M_MANUAL=Se abrir outra pagina, entre manualmente em:"
set "M_CERRAR=Para fechar: Ctrl+C ou feche esta janela."
set "M_FIN=O app foi fechado. Pressione uma tecla para sair..."
goto :inicio

:inicio
echo.
echo   ================================================================
echo     MV SQL NLP  -  !M_LEMA!
echo   ================================================================
echo.

:: -- 1. Detectar Python -----------------------------------------------
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
    for %%P in (
        "%LocalAppData%\Programs\Python\Python313\python.exe"
        "%LocalAppData%\Programs\Python\Python312\python.exe"
        "%LocalAppData%\Programs\Python\Python311\python.exe"
        "%ProgramFiles%\Python312\python.exe"
        "%UserProfile%\anaconda3\python.exe"
        "%UserProfile%\miniconda3\python.exe"
    ) do ( if exist %%P if not defined PY set "PY=%%~P" )
)
if not defined PY (
    color 0C
    echo   !M_NOPY!
    echo.
    echo   !M_BAJAR!
    echo   !M_PATH!
    echo.
    echo   !M_TECLA!
    pause >nul
    start https://www.python.org/downloads/
    exit /b 1
)
echo   [1/6] !M_PY! %PY%

:: -- 2. Entorno virtual -------------------------------------------------
:: Si un intento anterior se corto a la mitad (tipico: se lleno el disco),
:: queda un .venv incompleto: existe la carpeta pero no el python. Sin
:: esto, el reintento lo daba por bueno y fallaba mas adelante con un
:: error que no tenia nada que ver.
if exist ".venv" if not exist ".venv\Scripts\python.exe" rmdir /s /q ".venv" >nul 2>&1

if not exist ".venv\Scripts\python.exe" (
    echo   [2/6] !M_VENV_NEW!
    %PY% -m venv .venv || ( color 0C & echo   !M_VENV_ERR! & pause & exit /b 1 )
) else (
    echo   [2/6] !M_VENV_OK!
)
set "VPY=.venv\Scripts\python.exe"

:: -- 3. Dependencias ------------------------------------------------------
"%VPY%" -c "import streamlit, plotly, sklearn, openpyxl, reportlab" >nul 2>&1
if not errorlevel 1 (
    echo   [3/6] !M_DEPS_OK!
    goto :extras
)

:: Chequeo de disco ANTES de bajar nada. El nucleo instalado ocupa ~750 MB;
:: con el margen de la descarga y el descomprimido, abajo de 1.5 GB libres
:: la instalacion se corta por la mitad. Avisar antes es mejor que fallar a
:: los 4 minutos con el disco lleno.
:: En MB y entero a proposito: un decimal se imprime con coma en los Windows
:: en espanol/portugues, y ahi la comparacion numerica de cmd.exe se rompe en
:: silencio (el chequeo pasaria siempre, que es peor que no tenerlo).
:: Todo esto va FUERA de un bloque ( ): las lineas :: adentro de parentesis
:: rompen cmd.exe con "sintaxis incorrecta".
set "LIBRE_MB="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "try{[int]((Get-PSDrive -Name (Split-Path -Qualifier (Get-Location)).TrimEnd(':')).Free/1MB)}catch{''}" 2^>nul`) do set "LIBRE_MB=%%F"
if not defined LIBRE_MB goto :disco_ok
if !LIBRE_MB! GEQ 1536 goto :disco_ok
color 0C
echo   !M_DISCO_POCO!
echo       !M_DISCO_LIBRE! !LIBRE_MB! MB
echo       !M_DISCO_NEC!
echo.
echo   !M_DISCO_COMO!
pause & exit /b 1

:disco_ok
echo   [3/6] !M_DEPS!
"%VPY%" -m pip install --upgrade pip --quiet --no-cache-dir >nul 2>&1
:: --no-cache-dir: sin esto pip guarda una copia de cada wheel en
:: %LocalAppData%\pip\Cache ademas de instalarla, casi duplicando el espacio
:: que hace falta justo en el peor momento.
:: El log completo se guarda: es lo que permite decir QUE fallo, en vez de
:: mandar al cliente a revisar la conexion cuando el problema era el disco.
"%VPY%" -m pip install -r requirements.txt --no-cache-dir > "instalacion.log" 2>&1
if errorlevel 1 goto :deps_fallo

:extras
:: Extras opcionales (pyarrow, shap, faker): pesan casi lo mismo que medio
:: nucleo y el codigo ya los esquiva con try/except. Si fallan, NO se corta.
:: El marcador evita reintentar en cada arranque, y evita tener que hacer
:: "import shap" cada vez solo para saber si esta, que sola esa importacion
:: se lleva un par de segundos en cada inicio.
if exist ".extras_ok" goto :deps_listo
echo         !M_EXTRAS!
"%VPY%" -m pip install -r requirements-extras.txt --no-cache-dir >> "instalacion.log" 2>&1
if errorlevel 1 (
    echo         !M_EXTRAS_NO!
) else (
    echo ok> ".extras_ok"
)
goto :deps_listo

:deps_fallo
:: Diagnostico real, leyendo el log de pip. Antes cualquier fallo decia
:: "revisa tu conexion", que manda a buscar el problema al lugar
:: equivocado: el caso mas comun en una PC de oficina es el disco lleno.
color 0C
echo   !M_DEPS_ERR!
echo.
findstr /i /c:"No space left" /c:"Errno 28" /c:"not enough space" /c:"disk is full" "instalacion.log" >nul 2>&1
if not errorlevel 1 ( echo   ^>^> !M_E_DISCO! & echo      !M_DISCO_COMO! & goto :deps_fin )
findstr /i /c:"Errno 13" /c:"Access is denied" /c:"Permission denied" /c:"WinError 5" "instalacion.log" >nul 2>&1
if not errorlevel 1 ( echo   ^>^> !M_E_PERM! & echo      !M_E_PERM2! & goto :deps_fin )
findstr /i /c:"Could not find a version" /c:"requires a different Python" /c:"no matching distribution" "instalacion.log" >nul 2>&1
if not errorlevel 1 ( echo   ^>^> !M_E_PYVER! & %PY% --version & goto :deps_fin )
findstr /i /c:"ConnectionError" /c:"Temporary failure" /c:"Max retries" /c:"SSLError" /c:"ProxyError" /c:"Network is unreachable" "instalacion.log" >nul 2>&1
if not errorlevel 1 ( echo   ^>^> !M_E_RED! & goto :deps_fin )
echo   ^>^> !M_E_OTRO!
echo      %~dp0instalacion.log

:deps_fin
echo.
echo   !M_LOG!
powershell -NoProfile -Command "Get-Content 'instalacion.log' -Tail 6" 2>nul
echo.
pause & exit /b 1

:deps_listo

:: -- 4. Base demo -----------------------------------------------------------
if not exist "cartera_demo.db" (
    echo   [4/6] !M_DEMO!
    "%VPY%" generar_db_demo.py || echo   !M_DEMO_ERR!
) else (
    echo   [4/6] !M_DEMO_OK!
)

:: -- 5. Accesos directos (opcional, solo la primera vez) ----------------
:: Crea "MV SQL NLP" en el Escritorio y en el Menu Inicio, apuntando a
:: este mismo launcher, con el icono de MV. Solo pregunta una vez.
if not exist ".accesos_ok" (
    echo.
    choice /c SNY /n /m "!M_ACC_PREG!"
    set "CREAR="
    if not errorlevel 2 set "CREAR=1"
    if errorlevel 3 set "CREAR=1"
    if defined CREAR (
        set "MVSQL_DIR=%~dp0"
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
          "$dir=$env:MVSQL_DIR.TrimEnd('\');" ^
          "$w=New-Object -ComObject WScript.Shell;" ^
          "$ico=Join-Path $dir 'mvsql.ico';" ^
          "foreach($base in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))){" ^
          "  $s=$w.CreateShortcut((Join-Path $base 'MV SQL NLP.lnk'));" ^
          "  $s.TargetPath=(Join-Path $dir 'INICIAR_MVSQL.bat');" ^
          "  $s.WorkingDirectory=$dir;" ^
          "  if(Test-Path $ico){$s.IconLocation=$ico};" ^
          "  $s.Description='MV SQL NLP';" ^
          "  $s.Save() }" >nul 2>&1
        if exist "%UserProfile%\Desktop\MV SQL NLP.lnk" (
            echo   [5/6] !M_ACC_SI!
        ) else (
            echo   [5/6] !M_ACC_ONE!
            echo         !M_ACC_ONE2!
        )
    ) else (
        echo   [5/6] !M_ACC_NO!
    )
    echo ok> ".accesos_ok"
) else (
    echo   [5/6] !M_ACC_OK!
)

:: -- 6. Lanzar ----------------------------------------------------------------
:: Puerto fijo poco comun (8791) para no chocar con otras apps que uses
:: en tu PC (muchos programas usan el 8501 por defecto de Streamlit).
set "MVSQL_PORT=8791"
echo   [6/6] !M_INICIA! http://localhost:%MVSQL_PORT% ...
echo.
echo   ================================================================
echo    !M_ABRE!
echo    !M_MANUAL!
echo    http://localhost:%MVSQL_PORT%
echo    !M_CERRAR!
echo   ================================================================
echo.
"%VPY%" -m streamlit run app.py --server.port %MVSQL_PORT% --server.headless false --browser.gatherUsageStats false --theme.base dark

echo.
echo   !M_FIN!
pause >nul
