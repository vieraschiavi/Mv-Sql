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
set "M_DEPS_ERR=[X] Fallo instalando dependencias. Revisa tu conexion."
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
set "M_DEPS_ERR=[X] Could not install dependencies. Check your connection."
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
set "M_DEPS_ERR=[X] Falha ao instalar dependencias. Verifique sua conexao."
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
if not exist ".venv\Scripts\python.exe" (
    echo   [2/6] !M_VENV_NEW!
    %PY% -m venv .venv || ( color 0C & echo   !M_VENV_ERR! & pause & exit /b 1 )
) else (
    echo   [2/6] !M_VENV_OK!
)
set "VPY=.venv\Scripts\python.exe"

:: -- 3. Dependencias ------------------------------------------------------
"%VPY%" -c "import streamlit, plotly, sklearn, openpyxl, reportlab" >nul 2>&1
if errorlevel 1 (
    echo   [3/6] !M_DEPS!
    "%VPY%" -m pip install --upgrade pip --quiet
    "%VPY%" -m pip install -r requirements.txt --quiet || (
        color 0C & echo   !M_DEPS_ERR! & pause & exit /b 1 )
) else (
    echo   [3/6] !M_DEPS_OK!
)

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
