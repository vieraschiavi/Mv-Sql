; ============================================================================
; mvsql.nsi — instalador profesional de Windows para MV SQL NLP
; ============================================================================
; Compila con NSIS 3 (makensis). Genera un .exe que:
;   - deja elegir la carpeta de instalacion (paso obligatorio del pedido)
;   - no necesita permisos de administrador (instala en el perfil del
;     usuario, como VS Code o Slack: muchas PCs de oficina no dan admin)
;   - crea accesos directos de Escritorio y Menu Inicio con el icono de MV
;   - aparece en "Aplicaciones y caracteristicas" / "Add or Remove
;     Programs" de Windows, con desinstalador real
;   - instalador y desinstalador en espanol, ingles y portugues
;
; Lo que NO hace (y por que): no empaqueta Python ni las dependencias.
; Reusa exactamente el primer arranque ya probado de INICIAR_MVSQL.bat
; (detecta Python, crea un entorno virtual propio, instala dependencias,
; genera la base demo). Empaquetar un Python embebido con todas las
; ruedas (scikit-learn, shap, pyodbc...) es un proyecto aparte y hoy no
; esta probado; preferible no fingir que el instalador lo resuelve.
;
;   Compilar:  makensis installer\mvsql.nsi
;   Version:   makensis /DVERSION=1.2.3 installer\mvsql.nsi
; ============================================================================

Unicode true

!ifndef VERSION
  !define VERSION "1.0.0"
!endif

!define PRODUCT_NAME "MV SQL NLP"
!define PRODUCT_PUBLISHER "MV SQL NLP"
!define PRODUCT_WEB "https://mvsqlnlp.com"
!define APP_SRC "..\app-python"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MVSQLNLP"

Name "${PRODUCT_NAME}"
; Nombre de archivo estable (sin la version en el nombre): la web enlaza
; directo a este .exe, igual que ya hace con mvsql-nlp-app.zip. La version
; real vive en el registro (DisplayVersion) y en las propiedades del
; archivo (VIProductVersion), no en el nombre del archivo.
OutFile "..\web\downloads\MV-SQL-NLP-Setup.exe"
; Instala en el perfil del usuario: sin esto, escribir en Archivos de
; programa pide permisos de administrador que muchas PCs de empresa no
; dan a diario. El usuario igual puede elegir otra carpeta en el paso
; siguiente si prefiere instalar para todos.
InstallDir "$LOCALAPPDATA\Programs\MV SQL NLP"
RequestExecutionLevel user
SetCompressor /SOLID lzma

; -- Propiedades de archivo de Windows (boton derecho > Propiedades) --
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "Instalador de ${PRODUCT_NAME}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "(c) 2026 ${PRODUCT_PUBLISHER}"

; ----------------------------------------------------------------------
; Interfaz moderna (Modern UI 2)
; ----------------------------------------------------------------------
!include "MUI2.nsh"
!include "FileFunc.nsh"
!insertmacro GetSize

!define MUI_ICON "${APP_SRC}\mvsql.ico"
!define MUI_UNICON "${APP_SRC}\mvsql.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH

; -- Paginas del instalador --
; MUI_PAGE_LICENSE solo referencia "$(LICENSE_TEXT)" por nombre aca: el
; contenido real se declara mas abajo con LicenseLangString, despues del
; bloque de idiomas (MUI2 exige que las paginas se inserten ANTES que
; !insertmacro MUI_LANGUAGE, pero el valor del LangString puede resolverse
; despues — mismo patron que ya se usaba con TXT_FinishRun).
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "$(LICENSE_TEXT)"
!insertmacro MUI_PAGE_DIRECTORY
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "${UNINST_KEY}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "StartMenuFolder"
Var StartMenuFolder
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN "$INSTDIR\INICIAR_MVSQL.bat"
!define MUI_FINISHPAGE_RUN_TEXT "$(TXT_FinishRun)"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\LEEME.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "$(TXT_FinishReadme)"
!insertmacro MUI_PAGE_FINISH

; -- Paginas del desinstalador --
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; -- Idiomas: espanol primero (idioma por defecto), ingles, portugues --
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "PortugueseBR"

; -- Dialogo de seleccion de idioma: sin esto, NSIS elige el idioma en
; silencio segun el locale de Windows (en vez de preguntar o usar el
; espanol como default), que es un bug real que se vio al probar el
; instalador (arrancaba en ingles aunque espanol figura primero arriba).
; Se guarda la eleccion en el registro para que el desinstalador recuerde
; el mismo idioma sin volver a preguntar.
!define MUI_LANGDLL_REGISTRY_ROOT "HKCU"
!define MUI_LANGDLL_REGISTRY_KEY "${UNINST_KEY}"
!define MUI_LANGDLL_REGISTRY_VALUENAME "InstallerLanguage"

Function .onInit
  !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

Function un.onInit
  !insertmacro MUI_UNGETLANGUAGE
FunctionEnd

; -- Licencia: un texto distinto por idioma (LicenseLangString es el
; mecanismo de MUI2 para esto; sin esto, el EULA queda fijo en un solo
; idioma sin importar que idioma haya elegido el usuario) --
LicenseLangString LICENSE_TEXT ${LANG_SPANISH} "..\desktop\build\LICENSE.txt"
LicenseLangString LICENSE_TEXT ${LANG_ENGLISH} "..\desktop\build\LICENSE_en.txt"
LicenseLangString LICENSE_TEXT ${LANG_PORTUGUESEBR} "..\desktop\build\LICENSE_pt.txt"

; ----------------------------------------------------------------------
; Textos propios, en los 3 idiomas (los de MUI ya vienen traducidos)
; ----------------------------------------------------------------------
LangString TXT_FinishRun ${LANG_SPANISH} "Iniciar MV SQL NLP ahora"
LangString TXT_FinishRun ${LANG_ENGLISH} "Start MV SQL NLP now"
LangString TXT_FinishRun ${LANG_PORTUGUESEBR} "Iniciar o MV SQL NLP agora"

LangString TXT_FinishReadme ${LANG_SPANISH} "Ver el LEEME (primeros pasos)"
LangString TXT_FinishReadme ${LANG_ENGLISH} "View the README (getting started)"
LangString TXT_FinishReadme ${LANG_PORTUGUESEBR} "Ver o LEIA-ME (primeiros passos)"

LangString TXT_UninstAskData ${LANG_SPANISH} "Tambien encontramos datos tuyos: usuarios del equipo, auditoria, tu licencia y/o el contador de tu prueba gratuita.$\r$\n$\r$\n¿Querés borrarlos tambien? Elegi 'No' para conservarlos por si reinstalas mas adelante (ojo: borrar el contador de prueba reinicia los 7 dias)."
LangString TXT_UninstAskData ${LANG_ENGLISH} "We also found your data: team users, the audit log, your license and/or your free-trial counter.$\r$\n$\r$\nDo you want to delete it too? Choose 'No' to keep it in case you reinstall later (note: deleting the trial counter restarts the 7 days)."
LangString TXT_UninstAskData ${LANG_PORTUGUESEBR} "Tambem encontramos seus dados: usuarios da equipe, auditoria, sua licenca e/ou o contador do seu teste gratis.$\r$\n$\r$\nQuer apagar tambem? Escolha 'Nao' para manter, caso reinstale depois (atencao: apagar o contador do teste reinicia os 7 dias)."

LangString TXT_UninstDone ${LANG_SPANISH} "MV SQL NLP se desinstalo correctamente."
LangString TXT_UninstDone ${LANG_ENGLISH} "MV SQL NLP was successfully uninstalled."
LangString TXT_UninstDone ${LANG_PORTUGUESEBR} "O MV SQL NLP foi desinstalado com sucesso."

; ----------------------------------------------------------------------
; Instalacion
; ----------------------------------------------------------------------
Section "MV SQL NLP" SEC_MAIN
  SectionIn RO
  SetOutPath "$INSTDIR"

  ; Mismos archivos y mismas exclusiones que tools/empaquetar_zip.py
  ; (tests/, __pycache__/, .venv/ y los datos del cliente quedan afuera).
  File "${APP_SRC}\app.py"
  File "${APP_SRC}\auditoria.py"
  File "${APP_SRC}\catalogo.py"
  File "${APP_SRC}\conectores.py"
  File "${APP_SRC}\cuadernos.py"
  File "${APP_SRC}\equipo.py"
  File "${APP_SRC}\esquema_visual.py"
  File "${APP_SRC}\exportar.py"
  File "${APP_SRC}\generar_db_demo.py"
  File "${APP_SRC}\guardadas.py"
  File "${APP_SRC}\licencia.py"
  File "${APP_SRC}\motor.py"
  File "${APP_SRC}\proveedores_ia.py"
  File "${APP_SRC}\requirements.txt"
  File "${APP_SRC}\mvsql.ico"
  File "${APP_SRC}\INICIAR_MVSQL.bat"
  File "${APP_SRC}\CONECTAR_CLAUDE_MCP.bat"
  File "${APP_SRC}\LEEME.txt"

  ; El instalador ya crea los accesos directos "de verdad" (con carpeta
  ; de Menu Inicio elegida por el usuario, registro de desinstalador,
  ; etc). Sin este marcador, INICIAR_MVSQL.bat volveria a preguntar y a
  ; crear los suyos propios la primera vez que se lo abre.
  FileOpen $0 "$INSTDIR\.accesos_ok" w
  FileWrite $0 "instalador"
  FileClose $0

  ; -- Accesos directos --
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\MV SQL NLP.lnk" \
      "$INSTDIR\INICIAR_MVSQL.bat" "" "$INSTDIR\mvsql.ico" 0 \
      SW_SHOWMINIMIZED
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Desinstalar MV SQL NLP.lnk" \
      "$INSTDIR\Uninstall.exe"
  !insertmacro MUI_STARTMENU_WRITE_END
  CreateShortCut "$DESKTOP\MV SQL NLP.lnk" "$INSTDIR\INICIAR_MVSQL.bat" \
    "" "$INSTDIR\mvsql.ico" 0 SW_SHOWMINIMIZED

  ; -- Desinstalador + entrada en "Aplicaciones y caracteristicas" --
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\mvsql.ico"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "${UNINST_KEY}" "EstimatedSize" "$0"
SectionEnd

; ----------------------------------------------------------------------
; Desinstalacion
; ----------------------------------------------------------------------
Section "Uninstall"
  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
  Delete "$SMPROGRAMS\$StartMenuFolder\MV SQL NLP.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Desinstalar MV SQL NLP.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"
  Delete "$DESKTOP\MV SQL NLP.lnk"

  ; El entorno virtual y el codigo se borran siempre.
  RMDir /r "$INSTDIR\.venv"
  RMDir /r "$INSTDIR\__pycache__"
  Delete "$INSTDIR\*.py"
  Delete "$INSTDIR\*.bat"
  Delete "$INSTDIR\*.txt"
  Delete "$INSTDIR\*.ico"
  Delete "$INSTDIR\.accesos_ok"
  Delete "$INSTDIR\.idioma"
  Delete "$INSTDIR\Uninstall.exe"

  ; Los datos del cliente (usuarios, auditoria, base demo, licencia) se
  ; preguntan aparte: no es lo mismo desinstalar el programa que perder
  ; el registro de auditoria de una empresa. Se pregunta solo si hay
  ; algo de eso para preguntar.
  StrCpy $1 "0"
  IfFileExists "$INSTDIR\equipo.json" 0 +2
    StrCpy $1 "1"
  IfFileExists "$INSTDIR\auditoria.db" 0 +2
    StrCpy $1 "1"
  IfFileExists "$INSTDIR\cartera_demo.db" 0 +2
    StrCpy $1 "1"
  IfFileExists "$INSTDIR\licencia_mvsql.json" 0 +2
    StrCpy $1 "1"
  IfFileExists "$INSTDIR\.mvsql_trial.json" 0 +2
    StrCpy $1 "1"
  StrCmp $1 "0" fin_datos
  MessageBox MB_YESNO|MB_ICONQUESTION "$(TXT_UninstAskData)" IDNO fin_datos
    Delete "$INSTDIR\equipo.json"
    Delete "$INSTDIR\auditoria.db"
    Delete "$INSTDIR\cartera_demo.db"
    Delete "$INSTDIR\catalogo_demo.json"
    Delete "$INSTDIR\licencia_mvsql.json"
    Delete "$INSTDIR\.mvsql_trial.json"
  fin_datos:

  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${UNINST_KEY}"
  MessageBox MB_OK|MB_ICONINFORMATION "$(TXT_UninstDone)"
SectionEnd
