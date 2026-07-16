@echo off
setlocal EnableDelayedExpansion
title MV SQL NLP - Instalador y Launcher
color 0B

echo.
echo   ================================================================
echo     MV SQL NLP  -  Tu base de datos, en tu idioma
echo   ================================================================
echo.

cd /d "%~dp0"

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
    echo   [X] No se encontro Python instalado.
    echo.
    echo   Descargalo gratis de https://www.python.org/downloads/
    echo   IMPORTANTE: al instalar, marca "Add Python to PATH".
    echo.
    echo   Presiona una tecla para abrir la pagina de descarga...
    pause >nul
    start https://www.python.org/downloads/
    exit /b 1
)
echo   [1/6] Python detectado: %PY%

:: -- 2. Entorno virtual -------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo   [2/6] Creando entorno virtual aislado ^(solo la primera vez^)...
    %PY% -m venv .venv || ( color 0C & echo   [X] Fallo creando .venv & pause & exit /b 1 )
) else (
    echo   [2/6] Entorno virtual OK
)
set "VPY=.venv\Scripts\python.exe"

:: -- 3. Dependencias ------------------------------------------------------
"%VPY%" -c "import streamlit, plotly, sklearn, openpyxl, reportlab" >nul 2>&1
if errorlevel 1 (
    echo   [3/6] Instalando dependencias ^(2-5 min la primera vez^)...
    "%VPY%" -m pip install --upgrade pip --quiet
    "%VPY%" -m pip install -r requirements.txt --quiet || (
        color 0C & echo   [X] Fallo instalando dependencias. Revisa tu conexion. & pause & exit /b 1 )
) else (
    echo   [3/6] Dependencias OK
)

:: -- 4. Base demo -----------------------------------------------------------
if not exist "cartera_demo.db" (
    echo   [4/6] Generando base de datos demo...
    "%VPY%" generar_db_demo.py || echo   [!] No se pudo generar la demo ^(podes conectar tu propia base^)
) else (
    echo   [4/6] Base demo OK
)

:: -- 5. Accesos directos (opcional, solo la primera vez) ----------------
:: Crea "MV SQL NLP" en el Escritorio y en el Menu Inicio, apuntando a
:: este mismo launcher, con el icono de MV. Solo pregunta una vez.
if not exist ".accesos_ok" (
    echo.
    choice /c SN /n /m "  Crear acceso directo en Escritorio y Menu Inicio? [S/N]: "
    if not errorlevel 2 (
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
          "  $s.Description='MV SQL NLP - Tu base de datos, en tu idioma';" ^
          "  $s.Save() }" >nul 2>&1
        if exist "%UserProfile%\Desktop\MV SQL NLP.lnk" (
            echo   [5/6] Accesos directos creados: Escritorio y Menu Inicio
        ) else (
            echo   [5/6] Accesos creados ^(si no ves el del Escritorio, tu
            echo         Escritorio puede estar en OneDrive - busca "MV SQL NLP"
            echo         en el Menu Inicio^)
        )
    ) else (
        echo   [5/6] Sin accesos directos ^(no se vuelve a preguntar^)
    )
    echo ok> ".accesos_ok"
) else (
    echo   [5/6] Accesos directos OK
)

:: -- 6. Lanzar ----------------------------------------------------------------
:: Puerto fijo poco comun (8791) para no chocar con otras apps que uses
:: en tu PC (muchos programas usan el 8501 por defecto de Streamlit).
set "MVSQL_PORT=8791"
echo   [6/6] Iniciando MV SQL NLP en http://localhost:%MVSQL_PORT% ...
echo.
echo   ================================================================
echo    La app se abre sola en tu navegador.
echo    Si se abre otra pagina distinta, entra manualmente a:
echo    http://localhost:%MVSQL_PORT%
echo    Para cerrarla: Ctrl+C o cerra esta ventana.
echo   ================================================================
echo.
"%VPY%" -m streamlit run app.py --server.port %MVSQL_PORT% --server.headless false --browser.gatherUsageStats false --theme.base dark

echo.
echo   La app se cerro. Presiona una tecla para salir...
pause >nul
