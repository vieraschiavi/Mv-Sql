# © 2026 Martín Viera. Todos los derechos reservados.
"""
conector_aas.py — conectarse a Azure Analysis Services (el MDW) desde la barra lateral
=======================================================================================
Analysis Services habla DAX, no SQL. Esta conexión lee las tablas del modelo
(en solo lectura: sólo `EVALUATE`, con un tope de filas por tabla) y las deja en
una base SQLite temporal, que pasa por el mismo conector de solo lectura,
catálogo y validación que cualquier otra fuente.

Para hablar con Analysis Services hace falta el cliente ADOMD.NET de Microsoft
(pythonnet + pyadomd en Windows). Ese conector ya vive en la suite Adium All in
One (`adium_allinone.analysis_services`), con el usuario y contraseña corporativos,
la ventana de inicio de sesión de Microsoft (MFA) o un token. Cuando MV SQL NLP
corre adentro de la suite, se usa ése; suelto, se avisa qué hace falta.
"""
import re

AUTENTICACIONES = ("usuario", "ventana", "token")
TOPE_DEFAULT = 100_000
_ASAZURE = re.compile(r"^(asazure|powerbi)://\S+$", re.I)


class ErrorAAS(Exception):
    """Algo que el usuario tiene que corregir (dato faltante, permiso, librería)."""


def motor_suite():
    """El conector de Analysis Services de la suite, o None si MV SQL NLP corre suelto."""
    try:
        from adium_allinone import analysis_services
    except Exception:          # suelto: la suite no está en este proceso
        return None
    return analysis_services


def _validar_conexion(servidor, auth, usuario, clave, token):
    """Lo que hace falta para entrar al servidor (sin modelo: los modelos se listan después)."""
    servidor = (servidor or "").strip()
    if not _ASAZURE.match(servidor):
        raise ErrorAAS("El servidor empieza con asazure:// (o powerbi:// para un modelo de Power BI Premium).")
    if auth not in AUTENTICACIONES:
        raise ErrorAAS(f"Forma de entrar desconocida: {auth}.")
    if auth == "usuario" and not ((usuario or "").strip() and clave):
        raise ErrorAAS("Falta el usuario (tu mail de la empresa) o la contraseña.")
    if auth == "token" and not (token or "").strip():
        raise ErrorAAS("Falta el token.")
    return servidor


def _validar(servidor, modelo, auth, usuario, clave, token):
    if _ASAZURE.match((servidor or "").strip()) and not (modelo or "").strip():
        raise ErrorAAS("Falta el modelo: tocá «Ver los modelos del servidor» y elegilo de la lista.")
    return _validar_conexion(servidor, auth, usuario, clave, token), modelo.strip()


def _preparar(AS, servidor, auth, usuario, clave):
    faltan = AS.librerias_faltantes() if hasattr(AS, "librerias_faltantes") else []
    if faltan:
        detalle = AS.diagnostico_faltantes(faltan) if hasattr(AS, "diagnostico_faltantes") else ""
        raise ErrorAAS(f"Faltan librerías para hablar con Analysis Services: {', '.join(faltan)}. "
                       "En la suite: Pipeline → «Traer los módulos que faltan». " + detalle)
    try:
        AS.usar_usuario(servidor, usuario if auth == "usuario" else "", clave if auth == "usuario" else "")
        AS.usar_ventana(servidor, auth == "ventana")
    except Exception as e:     # p. ej. un usuario que no es un mail: el conector dice qué corregir
        raise ErrorAAS(str(e)) from e


def _suite_o_error(AS):
    AS = AS or motor_suite()
    if AS is None:
        raise ErrorAAS("Analysis Services se lee con el conector de Microsoft (ADOMD.NET) que trae Adium All in "
                       "One. Abrí MV SQL NLP desde la suite y conectate acá mismo.")
    return AS


def listar_modelos(servidor, auth="usuario", usuario="", clave="", token="", AS=None):
    """Los modelos (bases del MDW) del servidor que la cuenta puede ver: así no hay que saberse el nombre."""
    servidor = _validar_conexion(servidor, auth, usuario, clave, token)
    AS = _suite_o_error(AS)
    _preparar(AS, servidor, auth, usuario, clave)
    try:
        modelos = list(AS.listar_modelos(servidor, token if auth == "token" else ""))
    except Exception as e:     # permiso, red, MFA: el conector ya explica la causa
        raise ErrorAAS(str(e)) from e
    if not modelos:
        raise ErrorAAS("El servidor no devolvió modelos para esta cuenta (revisá el permiso de lectura sobre el "
                       "modelo, o escribí su nombre a mano).")
    return modelos


def listar_tablas(servidor, modelo, auth="usuario", usuario="", clave="", token="", AS=None):
    """Las tablas del modelo, para elegir cuáles traer."""
    servidor, modelo = _validar(servidor, modelo, auth, usuario, clave, token)
    AS = _suite_o_error(AS)
    _preparar(AS, servidor, auth, usuario, clave)
    try:
        return list(AS.tablas_del_modelo(servidor, modelo, token if auth == "token" else ""))
    except Exception as e:     # el conector ya explica la causa (permiso, red, MFA): se muestra tal cual
        raise ErrorAAS(str(e)) from e


def leer(servidor, modelo, auth="usuario", usuario="", clave="", token="", tablas=None,
         limite=TOPE_DEFAULT, AS=None):
    """Trae las tablas (todas o las elegidas) en solo lectura. Devuelve (etiqueta, {tabla: DataFrame}, avisos)."""
    servidor, modelo = _validar(servidor, modelo, auth, usuario, clave, token)
    AS = _suite_o_error(AS)
    _preparar(AS, servidor, auth, usuario, clave)
    try:
        lec = AS.leer(servidor, modelo, token if auth == "token" else "", tablas=list(tablas) if tablas else None,
                      limite=limite or None)
    except Exception as e:
        raise ErrorAAS(str(e)) from e
    con_datos = getattr(lec, "con_datos", None) or getattr(lec, "tablas", ())
    datos = {t.nombre: t.datos for t in con_datos}
    if not datos:
        raise ErrorAAS("El modelo no devolvió tablas con datos (revisá los permisos sobre el modelo).")
    return f"Analysis Services · {modelo}", datos, list(getattr(lec, "avisos", ()))
