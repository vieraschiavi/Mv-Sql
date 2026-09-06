# © 2026 Martín Viera. Todos los derechos reservados.

"""
frescura.py — ¿están al día los datos que estoy consultando?
==================================================================
Una consulta perfecta sobre una tabla que no se carga hace cinco días
devuelve un número perfecto y equivocado. Este módulo contesta, por cada
tabla del esquema, cuándo se cargó por última vez y si eso entra dentro
de la frecuencia esperada.

Cómo sabe cuál es la "fecha de carga", que es la parte difícil:

  1. Del CATÁLOGO saca qué columnas son de fecha/hora (por tipo, no por
     nombre: el tipo lo declara el motor y no se equivoca).
  2. Entre esas, elige por NOMBRE la que más se parece a una marca de
     carga. No es lo mismo `fecha_carga` que `fecha_nacimiento`: las dos
     son DATE, pero solo una dice cuándo entró el dato. El puntaje de
     PISTAS_NOMBRE ordena esa preferencia.
  3. Si ninguna columna de fecha tiene nombre reconocible, igual usa la
     primera de tipo fecha, pero lo marca como aproximado — es mejor un
     dato con reserva que ninguno, siempre que la reserva se vea.

Lo que NO hace, a propósito: no consulta metadatos internos del motor
(`sys.dm_db_index_usage_stats`, `pg_stat_user_tables`,
`information_schema.tables.UPDATE_TIME`). Esos valores se reinician al
reiniciar el servidor, no distinguen una carga real de un `ANALYZE`, y en
InnoDB suelen venir en NULL. Preguntarle a los datos cuándo son de verdad
es más lento pero es lo que el negocio llama "fecha de carga".

Solo lectura, como todo el producto: genera `SELECT MAX(...)` y nada más.
==================================================================
"""

import re
from datetime import datetime, timedelta

# Tipos que los cuatro motores usan para fecha/hora. Se compara contra el
# principio del tipo declarado, así entran variantes como
# "timestamp without time zone" o "datetime2(7)".
TIPOS_FECHA = (
    "date", "datetime", "datetime2", "smalldatetime", "datetimeoffset",
    "timestamp", "timestamptz",
)

# Qué tan bien el nombre de una columna indica "cuándo se cargó esto".
# Se busca como subcadena, en minúsculas y sin acentos, y gana el puntaje
# más alto. El orden importa: `fecha_carga` tiene que ganarle a
# `fecha_nacimiento` aunque las dos empiecen con "fecha".
PISTAS_NOMBRE = (
    ("carga", 100), ("load", 100), ("etl", 95), ("ingest", 95),
    ("proceso", 90), ("batch", 90), ("extract", 85),
    ("actualiz", 80), ("updated", 80), ("update", 80),
    ("modif", 70), ("modified", 70),
    ("insert", 60), ("creado", 55), ("created", 55), ("alta", 50),
    # De acá para abajo el nombre solo dice "esto es una fecha", no "esta
    # es la fecha en que entró el dato". Sirven para elegir algo cuando no
    # hay nada mejor, pero NO alcanzan para afirmar nada.
    ("fecha", 30), ("date", 30), ("timestamp", 25), ("hora", 20),
)

# A partir de qué puntaje la columna se considera una marca de carga de
# verdad. Sin este umbral, `fecha_nacimiento` calificaba como confiable
# —contiene "fecha"— y el panel informaba con total seguridad que la tabla
# de clientes estaba atrasada 8653 días. Probado contra la base demo: es
# el caso que convierte el panel en algo que miente con confianza.
UMBRAL_CONFIABLE = 50

# Cada cuánto se espera que llegue el dato, y a partir de cuántas horas
# sin novedad se considera atrasada. El margen extra sobre el período no
# es capricho: un proceso diario que corre a las 3 AM y se mira a las 9 AM
# tiene 30 horas de antigüedad y está perfecto.
FRECUENCIAS = {
    "diaria":   {"horas": 36},
    "semanal":  {"horas": 24 * 8},
    "mensual":  {"horas": 24 * 33},
}
FRECUENCIA_DEFECTO = "diaria"

# Identificador SQL simple. Los nombres salen del catálogo (los declaró el
# motor, no el usuario), pero se validan igual antes de interpolarlos: es
# el único lugar del módulo donde un nombre entra al texto del SQL, y una
# barrera que solo funciona "porque el origen es confiable" deja de
# funcionar el día que alguien le cambia el origen.
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def _sin_acentos(texto):
    tabla = str.maketrans("áéíóúàèìòùäëïöüâêîôûñ", "aeiouaeiouaeiouaeioun")
    return str(texto).lower().translate(tabla)


def es_columna_fecha(tipo):
    """True si el tipo declarado por el motor es de fecha/hora.

    `time` queda afuera a propósito: una hora sin fecha no dice de qué
    día es el dato, que es justo lo que se quiere saber acá.
    """
    t = _sin_acentos(tipo or "").strip()
    return any(t.startswith(p) for p in TIPOS_FECHA)


def puntaje_nombre(columna):
    """Qué tan bien el nombre indica una marca de carga (0 = nada)."""
    n = _sin_acentos(columna)
    mejor = 0
    for pista, puntos in PISTAS_NOMBRE:
        if pista in n and puntos > mejor:
            mejor = puntos
    return mejor


def elegir_columna(info_tabla):
    """La mejor columna de fecha de una tabla del catálogo.

    Devuelve (columna, seguro) donde `seguro` es False cuando se eligió
    una columna de fecha cuyo nombre no dice nada de cargas — sirve, pero
    la pantalla tiene que mostrarlo como aproximado en vez de afirmarlo.
    Devuelve (None, False) si la tabla no tiene ninguna columna de fecha.
    """
    candidatas = [c["columna"] for c in info_tabla.get("columnas", [])
                  if es_columna_fecha(c.get("tipo"))]
    if not candidatas:
        return None, False
    # max() con clave (puntaje, -índice) para que ante empate gane la
    # primera declarada, y no una cualquiera según el orden interno.
    mejor = max(enumerate(candidatas), key=lambda par: (puntaje_nombre(par[1]), -par[0]))[1]
    return mejor, puntaje_nombre(mejor) >= UMBRAL_CONFIABLE


def _citar(nombre, dialecto):
    """Cita un identificador según el motor. Lanza si no es un nombre simple."""
    partes = str(nombre).split(".")          # esquema.tabla
    for p in partes:
        if not _IDENT.match(p):
            raise ValueError(f"Identificador no admitido: {nombre!r}")
    d = (dialecto or "").lower()
    if "sql server" in d:
        return ".".join(f"[{p}]" for p in partes)
    if "mysql" in d:
        return ".".join(f"`{p}`" for p in partes)
    return ".".join(f'"{p}"' for p in partes)   # SQLite y PostgreSQL


def sql_frescura(tabla, columna, dialecto):
    """El SELECT que pregunta por la última fecha cargada de una tabla.

    Solo MAX(): la cantidad de filas se toma del catálogo, que ya la trae.
    Un COUNT(*) acá obligaría a recorrer la tabla entera de cada objeto
    del esquema, que es exactamente el costo que este panel no puede
    permitirse para ser algo que se mira seguido.
    """
    return f"SELECT MAX({_citar(columna, dialecto)}) AS ultima_carga FROM {_citar(tabla, dialecto)}"


def _a_fecha(valor):
    """Normaliza a datetime lo que devuelva cada driver (str, date, datetime)."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if hasattr(valor, "year") and not hasattr(valor, "hour"):    # date
        return datetime(valor.year, valor.month, valor.day)
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "").strip())
    except ValueError:
        return None


def estado(ultima, ahora, frecuencia=FRECUENCIA_DEFECTO):
    """'al_dia' | 'atrasada' | 'sin_fecha', y la antigüedad en horas."""
    fecha = _a_fecha(ultima)
    if fecha is None:
        return "sin_fecha", None
    # Los datetimes con zona horaria no se pueden restar con los que no la
    # tienen. Se descarta la zona antes de comparar: acá interesa la
    # distancia en horas, no el instante absoluto.
    if fecha.tzinfo is not None:
        fecha = fecha.replace(tzinfo=None)
    horas = (ahora - fecha).total_seconds() / 3600.0
    limite = FRECUENCIAS.get(frecuencia, FRECUENCIAS[FRECUENCIA_DEFECTO])["horas"]
    # Una fecha futura no es "al día": es un reloj mal puesto o una carga
    # con fecha proyectada, y taparlo como verde esconde justo el problema.
    if horas < -1:
        return "futura", horas
    return ("al_dia" if horas <= limite else "atrasada"), horas


def analizar(conexion, catalogo, ahora=None, frecuencia=FRECUENCIA_DEFECTO,
             tablas=None, ejecutar=None):
    """Estado de carga de cada tabla del catálogo.

    `ejecutar` se inyecta en los tests para no necesitar una base real;
    por defecto usa el `ejecutar()` de la conexión, que es el mismo punto
    donde vive la barrera de solo lectura.

    Nunca lanza por una tabla: si una falla (permisos, tabla que ya no
    existe, tipo raro), esa fila queda con su error y las demás se
    informan igual. Un panel de monitoreo que se cae entero porque una de
    cuarenta tablas falló no sirve para monitorear nada.
    """
    ahora = ahora or datetime.now()
    correr = ejecutar or (lambda sql: conexion.ejecutar(sql, limite=1))
    dialecto = getattr(conexion, "dialecto", "") if conexion else ""

    filas = []
    for tabla, info in (catalogo.get("tablas") or {}).items():
        if tablas is not None and tabla not in tablas:
            continue
        columna, seguro = elegir_columna(info)
        fila = {
            "tabla": tabla,
            "columna": columna,
            "columna_confiable": seguro,
            "n_filas": info.get("n_filas"),
            "ultima_carga": None,
            "horas": None,
            "estado": "sin_fecha",
            "error": None,
        }
        if columna:
            try:
                _cols, datos, _sql = correr(sql_frescura(tabla, columna, dialecto))
                valor = datos[0][0] if datos and datos[0] else None
                fila["ultima_carga"] = _a_fecha(valor)
                fila["estado"], fila["horas"] = estado(valor, ahora, frecuencia)
            except Exception as e:                        # noqa: BLE001
                fila["estado"] = "error"
                fila["error"] = str(e)[:200]
        filas.append(fila)

    # Primero lo que necesita atención: atrasadas, después el resto.
    orden = {"atrasada": 0, "futura": 1, "error": 2, "sin_fecha": 3, "al_dia": 4}
    filas.sort(key=lambda f: (orden.get(f["estado"], 9), -(f["horas"] or 0)))
    return filas


def resumen(filas):
    """Conteo por estado, para las métricas de arriba del panel."""
    r = {"total": len(filas), "al_dia": 0, "atrasada": 0,
         "sin_fecha": 0, "error": 0, "futura": 0}
    for f in filas:
        if f["estado"] in r:
            r[f["estado"]] += 1
    return r


def antiguedad_legible(horas, idioma="es"):
    """'3 h' / '2 d 4 h' — la antigüedad en algo que se lee de un vistazo."""
    if horas is None:
        return "—"
    if horas < 0:
        horas = abs(horas)
    dias = int(horas // 24)
    resto = int(horas % 24)
    unidad_d = {"es": "d", "en": "d", "pt": "d"}[idioma if idioma in ("es", "en", "pt") else "es"]
    if dias:
        # "8654 d 0 h" es ruido: con días de por medio, las horas exactas
        # no cambian ninguna decisión.
        return f"{dias} {unidad_d} {resto} h" if resto else f"{dias} {unidad_d}"
    return f"{resto} h" if resto else "< 1 h"
