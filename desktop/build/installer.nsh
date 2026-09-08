# © 2026 Martín Viera. Todos los derechos reservados.

# MV SQL NLP — el instalador NO asume el disco C: como default
# ============================================================================
# electron-builder ya deja ELEGIR la carpeta (nsis.allowToChangeInstallationDirectory:
# true en electron-builder.yml) — el problema no era ese. El problema es que el
# DEFAULT que se ve al abrir esa pantalla siempre arrancaba en
# $LocalAppData\Programs\..., que vive en la unidad del perfil de Windows —
# casi siempre C:, sin importar si esa es la unidad con más lugar libre. En una
# PC con un SSD chico de sistema y un disco grande aparte (el caso real que
# motivó esto), el cliente tenía que darse cuenta solo de que existía el botón
# "Examinar" y saber a qué unidad ir.
#
# customInit es el hook que electron-builder deja insertar en el .onInit del
# instalador (ver node_modules/app-builder-lib/templates/nsis/installer.nsi),
# y corre DESPUÉS de initMultiUser — o sea que $INSTDIR ya tiene el default de
# siempre calculado, y $perUserInstallationFolder ya dice si esto es una
# reinstalación (leída del registro) o una instalación nueva.
#
# Reglas, en orden de importancia:
#
#   1) Si $perUserInstallationFolder NO está vacío, es una reinstalación o
#      actualización: la carpeta viene del registro, de una instalación que
#      YA EXISTE en esa unidad. Acá no se toca nada — mudar de disco una
#      instalación existente le rompería al cliente los datos y la config
#      que ya tenía ahí.
#   2) Si es instalación nueva, se compara el espacio libre de la unidad
#      default contra el de las demás unidades FIJAS (HDD en el sentido de
#      GetDrives: excluye red, CD-ROM y extraíbles — no tiene sentido
#      instalar "solo" en un pendrive) y se usa la que tenga más lugar,
#      preservando la misma subcarpeta (\Users\...\Programs\MV SQL NLP) en
#      la unidad elegida.
#   3) Si ninguna otra unidad tiene MÁS espacio que la default (el caso más
#      común: una sola unidad, o el sistema ya está en la más grande), no
#      cambia nada — mismo comportamiento de siempre.
#
# El cliente sigue pudiendo cambiar la carpeta a mano en la pantalla
# siguiente (Examinar): esto solo cambia qué aparece pre-cargado ahí.
# ============================================================================

# Estos dos !include NO son decorativos y no se pueden sacar "porque
# electron-builder ya los incluye". Rompieron un release de verdad:
#
#   Invalid command: "${DriveSpace}"
#   !include: error in script: "...\build\installer.nsh" on line 103
#
# El motivo es una asimetria de NSIS que es facil no ver. Lo que hay
# adentro de un !macro NO se expande al momento del !include: queda
# guardado tal cual y recien se resuelve cuando alguien lo inserta. Una
# Function, en cambio, se compila EN EL ACTO. Por eso el ${DriveSpace}
# de adentro de customInit pasaba sin chistar y el de la Function de
# abajo explotaba: cuando electron-builder mete este archivo, todavia no
# incluyo FileFunc.nsh.
#
# Los dos headers se auto-protegen contra la doble inclusion
# (!ifndef FILEFUNC_INCLUDED / LOGICLIB_INCLUDED), asi que incluirlos
# aca es gratis aunque electron-builder los incluya despues.
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!macro customInit
  ${If} $perUserInstallationFolder == ""
    Push $R1
    Push $R2
    Push $R3
    Push $R4
    Push $R5
    Push $R6

    ${GetRoot} "$INSTDIR" $R1
    StrCpy $R3 "$INSTDIR" "" 2   ; ej "\Users\yo\AppData\Local\Programs\MV SQL NLP"

    ; Punto de partida: la propia unidad default. Si nada le gana, no cambia
    ; nada — la comparacion de abajo es siempre "> ", nunca ">=".
    ${DriveSpace} "$R1\" "/D=F /S=M" $R4
    StrCpy $R5 $R1
    StrCpy $R6 $R4

    Push $R1
    Push $R3
    Push $R5
    Push $R6
    ${GetDrives} "HDD" "MvsqlInstallerEvaluarUnidad"
    Pop $R6
    Pop $R5
    Pop $R3
    Pop $R1

    ${If} $R5 != $R1
      StrCpy $INSTDIR "$R5$R3"
    ${EndIf}

    Pop $R6
    Pop $R5
    Pop $R4
    Pop $R3
    Pop $R2
    Pop $R1
  ${EndIf}

  ; Va FUERA del ${If}: elegir carpeta es cosa de la instalacion nueva, pero
  ; la carpeta temporal se llena igual cuando el cliente actualiza sobre una
  ; instalacion que ya existe.
  !insertmacro MvsqlChequearEspacio
!macroend

# ============================================================================
# Espacio libre: avisar ANTES, con un mensaje que se entienda
# ============================================================================
# El error que motivo esto, tal cual lo vio el cliente:
#
#   Extrayendo: error escribiendo al archivo
#   C:\Users\Martin\AppData\Local\Temp\nsx4368.tmp\app-64.7z
#
# Eso es NSIS volcando el paquete embebido en $PLUGINSDIR y quedandose sin
# lugar. El mensaje no dice "no hay espacio", no dice en que unidad, y no
# dice que hacer: dice una ruta temporal con un nombre al azar. El cliente
# que lo ve concluye, con razon, que el programa "le pide el disco C".
#
# Y en parte se lo pide: $PLUGINSDIR sale siempre de %TEMP%, que vive en la
# unidad del perfil de Windows aunque la instalacion vaya a otra unidad.
# Desde el script NO se puede mover: $TEMP es constante de solo lectura y
# `StrCpy $TEMP ...` ni siquiera compila (makensis: "Usage: StrCpy
# $(user_var: output) ..."). Asi que lo que si se puede hacer es dos cosas:
#
#   1) que la temporal necesite MUCHO menos lugar. Con useZip en
#      electron-builder.yml el paquete se descomprime directo a $INSTDIR en
#      vez de pasar por $PLUGINSDIR\7z-out, asi que la temporal solo tiene
#      que aguantar el archivo comprimido y no ademas la copia expandida.
#   2) avisar antes de empezar, diciendo unidad, cuanto hay, cuanto falta y
#      cual es la salida — que es lo que hace esto.
#
# El aviso NO corta por su cuenta: pregunta. La cuenta de abajo es una
# estimacion (60% del tamano descomprimido), y una estimacion equivocada
# que bloquea una instalacion que iba a andar es peor que el error feo.
!macro MvsqlChequearEspacio
  Push $R1
  Push $R2
  Push $R3

  ; Cuanto ocupa la app descomprimida, en MB. APP_64_UNPACKED_SIZE lo define
  ; electron-builder en KB (el mismo numero que usa para SectionSetSize).
  !ifdef APP_64_UNPACKED_SIZE
    IntOp $R3 ${APP_64_UNPACKED_SIZE} / 1024
  !else
    StrCpy $R3 400
  !endif

  ; --- carpeta temporal: el .zip embebido, ~60% de lo descomprimido ---
  ${GetRoot} "$TEMP" $R1
  ${DriveSpace} "$R1\" "/D=F /S=M" $R2
  IntOp $MvsqlNecesarios $R3 * 6
  IntOp $MvsqlNecesarios $MvsqlNecesarios / 10
  ${If} $R2 < $MvsqlNecesarios
    StrCpy $MvsqlUnidad $R1
    StrCpy $MvsqlLibres $R2
    StrCpy $MvsqlMotivo "T"
    Call MvsqlAvisarEspacio
  ${EndIf}

  ; --- carpeta de instalacion: la app entera ---
  ${GetRoot} "$INSTDIR" $R1
  ${DriveSpace} "$R1\" "/D=F /S=M" $R2
  ${If} $R2 < $R3
    StrCpy $MvsqlUnidad $R1
    StrCpy $MvsqlLibres $R2
    StrCpy $MvsqlNecesarios $R3
    StrCpy $MvsqlMotivo "I"
    Call MvsqlAvisarEspacio
  ${EndIf}

  Pop $R3
  Pop $R2
  Pop $R1
!macroend

Var MvsqlUnidad       ; ej "C:"
Var MvsqlLibres       ; MB libres en esa unidad
Var MvsqlNecesarios   ; MB que hacen falta
Var MvsqlMotivo       ; "T" = carpeta temporal · "I" = carpeta de instalacion
Var MvsqlEtiqueta     ; el renglon que nombra QUE espacio falta
Var MvsqlTexto        ; el mensaje armado, ya en el idioma del cliente

# Muestra el aviso en el idioma que el cliente eligio al abrir el instalador
# y corta si dice que no. $LANGUAGE ya esta resuelto acá: electron-builder
# inserta MUI_LANGDLL_DISPLAY en .onInit ANTES de customInit.
#
# Los IDs son los de los .nlf que usa electron-builder para
# installerLanguages: [es_ES, en_US, pt_BR] — ojo que es_ES no mapea a
# "Spanish" (1034) sino a "SpanishInternational" (3082). No se pueden usar
# las constantes ${LANG_*}: este archivo se incluye antes de los
# MUI_LANGUAGE que las definen. El castellano queda de fallback porque es
# el primer idioma de la lista, o sea el default del instalador.
Function MvsqlAvisarEspacio
  ${If} $LANGUAGE == 1033
    ${If} $MvsqlMotivo == "T"
      StrCpy $MvsqlEtiqueta "Windows temporary files"
    ${Else}
      StrCpy $MvsqlEtiqueta "Installation folder"
    ${EndIf}
    StrCpy $MvsqlTexto "Not enough free space on drive $MvsqlUnidad$\n$\n\
      $MvsqlEtiqueta$\n\
      Free: $MvsqlLibres MB   ·   Needed: $MvsqlNecesarios MB$\n$\n\
      Windows unpacks the installer in its temporary folder, which lives on \
      the profile drive even when you install the program somewhere else. \
      The installer cannot move it.$\n$\n\
      What you can do:$\n\
      · free up space on $MvsqlUnidad, or$\n\
      · download MV-SQL-NLP-${VERSION}.zip, which ships alongside this installer, unzip it \
      on any drive you like and run 'MV SQL NLP.exe'. It installs nothing.$\n$\n\
      If you continue, the installation will most likely fail while \
      extracting the files.$\n$\n\
      Continue anyway?"
  ${ElseIf} $LANGUAGE == 1046
    ${If} $MvsqlMotivo == "T"
      StrCpy $MvsqlEtiqueta "Arquivos temporários do Windows"
    ${Else}
      StrCpy $MvsqlEtiqueta "Pasta de instalação"
    ${EndIf}
    StrCpy $MvsqlTexto "Não há espaço suficiente na unidade $MvsqlUnidad$\n$\n\
      $MvsqlEtiqueta$\n\
      Livres: $MvsqlLibres MB   ·   Necessários: $MvsqlNecesarios MB$\n$\n\
      O Windows descompacta o instalador na sua pasta temporária, que fica \
      na unidade do perfil mesmo que você instale o programa em outra. O \
      instalador não pode mudá-la de lugar.$\n$\n\
      O que você pode fazer:$\n\
      · liberar espaço em $MvsqlUnidad, ou$\n\
      · baixar MV-SQL-NLP-${VERSION}.zip, que vem junto com este instalador, e descompactar na \
      unidade que quiser e executar 'MV SQL NLP.exe'. Não instala nada.$\n$\n\
      Se continuar, a instalação provavelmente vai falhar ao extrair os \
      arquivos.$\n$\n\
      Continuar mesmo assim?"
  ${Else}
    ${If} $MvsqlMotivo == "T"
      StrCpy $MvsqlEtiqueta "Archivos temporales de Windows"
    ${Else}
      StrCpy $MvsqlEtiqueta "Carpeta de instalación"
    ${EndIf}
    StrCpy $MvsqlTexto "No hay espacio suficiente en la unidad $MvsqlUnidad$\n$\n\
      $MvsqlEtiqueta$\n\
      Libres: $MvsqlLibres MB   ·   Necesarios: $MvsqlNecesarios MB$\n$\n\
      Windows descomprime el instalador en su carpeta temporal, que vive en \
      la unidad del perfil aunque instales el programa en otra. El \
      instalador no puede moverla.$\n$\n\
      Qué podés hacer:$\n\
      · liberar espacio en $MvsqlUnidad, o$\n\
      · descargar MV-SQL-NLP-${VERSION}.zip, que viene junto a este \
      instalador, descomprimirlo en la unidad que quieras y ejecutar \
      'MV SQL NLP.exe'. \
      No instala nada.$\n$\n\
      Si seguís igual, la instalación probablemente falle al extraer los \
      archivos.$\n$\n\
      ¿Continuar de todos modos?"
  ${EndIf}

  MessageBox MB_YESNO|MB_ICONEXCLAMATION "$MvsqlTexto" /SD IDYES IDYES +2
    Quit
FunctionEnd

# Callback de ${GetDrives}: recibe la letra de unidad (ej "D:\") en $0 y
# tiene que terminar empujando algo a la pila para que la enumeracion
# siga (cualquier valor sirve, salvo el string "StopGetDrives", que la
# cortaria antes de tiempo — no quiero cortarla, quiero ver TODAS las
# unidades fijas para quedarme con la de mas espacio).
#
# $R1/$R3/$R5/$R6 viajan en la pila (no como variables globales) porque
# ${GetDrives} no garantiza preservar el valor de las variables $R* entre
# una llamada al callback y la siguiente — sacarlas de la pila en cada
# vuelta es lo unico que no depende de esa garantia.
Function MvsqlInstallerEvaluarUnidad
  Exch $0        ; $0 = unidad que ofrece GetDrives, ej "D:\"
  Exch 4
  Pop $R1
  Exch 3
  Pop $R3
  Exch 2
  Pop $R5
  Exch 1
  Pop $R6

  ${DriveSpace} "$0" "/D=F /S=M" $1
  ${If} $1 > $R6
    StrCpy $R5 $0
    StrCpy $R6 $1
  ${EndIf}

  Push $R6
  Push $R5
  Push $R3
  Push $R1
  Push $0        ; valor de continuacion para GetDrives (no es "StopGetDrives")
FunctionEnd
