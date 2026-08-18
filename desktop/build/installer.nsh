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
!macroend

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
