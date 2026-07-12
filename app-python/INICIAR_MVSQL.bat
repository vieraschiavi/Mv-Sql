@echo off
setlocal EnableDelayedExpansion
title MV SQL NLP - Instalador y Launcher
color 0B
chcp 65001 >nul 2>&1

echo.
echo   ███╗   ███╗██╗   ██╗    ███████╗ ██████╗ ██╗
echo   ████╗ ████║██║   ██║    ██╔════╝██╔═══██╗██║
echo   ██╔████╔██║██║   ██║    ███████╗██║   ██║██║
echo   ██║╚██╔╝██║╚██╗ ██╔╝    ╚════██║██║▄▄ ██║██║
echo   ██║ ╚═╝ ██║ ╚████╔╝     ███████║╚██████╔╝███████╗
echo   ╚═╝     ╚═╝  ╚═══╝      ╚══════╝ ╚══▀▀═╝ ╚══════╝
echo               N  L  P   ·   Tu base de datos, en tu idioma
echo   ─────────────────────────────────────────────────────────
echo.

cd /d "%~dp0"

:: ── 1. Detectar Python ─────────────────────────────────────────
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
echo   [1/5] Python detectado: %PY%

:: ── 2. Entorno virtual ─────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo   [2/5] Creando entorno virtual aislado ^(solo la primera vez^)...
    %PY% -m venv .venv || ( color 0C & echo   [X] Fallo creando .venv & pause & exit /b 1 )
) else (
    echo   [2/5] Entorno virtual OK
)
set "VPY=.venv\Scripts\python.exe"

:: ── 3. Dependencias ────────────────────────────────────────────
"%VPY%" -c "import streamlit, plotly, sklearn, openpyxl, reportlab" >nul 2>&1
if errorlevel 1 (
    echo   [3/5] Instalando dependencias ^(2-5 min la primera vez^)...
    "%VPY%" -m pip install --upgrade pip --quiet
    "%VPY%" -m pip install -r requirements.txt --quiet || (
        color 0C & echo   [X] Fallo instalando dependencias. Revisa tu conexion. & pause & exit /b 1 )
) else (
    echo   [3/5] Dependencias OK
)

:: ── 4. Base demo ───────────────────────────────────────────────
if not exist "cartera_demo.db" (
    echo   [4/5] Generando base de datos demo...
    "%VPY%" generar_db_demo.py || echo   [!] No se pudo generar la demo ^(podes conectar tu propia base^)
) else (
    echo   [4/5] Base demo OK
)

:: ── 5. Lanzar ──────────────────────────────────────────────────
echo   [5/5] Iniciando MV SQL NLP en http://localhost:8501 ...
echo.
echo   ─────────────────────────────────────────────────────────
echo    La app se abre sola en tu navegador.
echo    Para cerrarla: Ctrl+C o cerra esta ventana.
echo   ─────────────────────────────────────────────────────────
echo.
"%VPY%" -m streamlit run app.py --server.headless false --browser.gatherUsageStats false --theme.base dark
pause
