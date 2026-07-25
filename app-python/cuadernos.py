"""
cuadernos.py — MV SQL NLP
==================================================================
Cuadernos: informes reutilizables que mezclan texto (Markdown),
preguntas en lenguaje natural y SQL, con VARIABLES compartidas entre
todas las celdas.

Para qué sirve de verdad: el informe mensual de cobranzas se arma una
vez con {{mes}} y {{sucursal}} como variables, y el mes que viene se
vuelve a correr entero cambiando un valor. Es la diferencia entre
"hice una consulta" y "tengo un informe".

Las variables se escriben {{nombre}} y se sustituyen SIEMPRE como
parámetros del motor de base de datos, nunca pegando el texto en el
SQL: así una variable con comillas o un `DROP TABLE` no puede
convertirse en inyección.

Se guardan en JSON local, junto a las consultas guardadas.
==================================================================
"""

import json
import os
import re
from datetime import datetime

ARCHIVO = os.path.join(os.path.expanduser("~"), ".mvsql", "cuadernos.json")

# {{variable}} — nombre simple, sin espacios ni símbolos raros
PATRON_VAR = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")

TIPOS_CELDA = ("markdown", "pregunta", "sql")


def _cargar():
    if not os.path.exists(ARCHIVO):
        return []
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _persistir(items):
    os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)
    tmp = ARCHIVO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARCHIVO)


# ──────────────────────────────────────────────────────────────
# Variables
# ──────────────────────────────────────────────────────────────
def variables_usadas(texto: str) -> list:
    """Nombres de variables que aparecen en un texto, sin repetir y en orden."""
    vistas, orden = set(), []
    for m in PATRON_VAR.finditer(texto or ""):
        if m.group(1) not in vistas:
            vistas.add(m.group(1))
            orden.append(m.group(1))
    return orden


def variables_del_cuaderno(cuaderno: dict) -> list:
    """Todas las variables que usa el cuaderno, en orden de aparición."""
    vistas, orden = set(), []
    for celda in cuaderno.get("celdas", []):
        for v in variables_usadas(celda.get("contenido", "")):
            if v not in vistas:
                vistas.add(v)
                orden.append(v)
    return orden


def sustituir_texto(texto: str, valores: dict) -> str:
    """Reemplaza {{var}} por su valor. Solo para Markdown y preguntas —
    NUNCA para el SQL que se ejecuta (ver `preparar_sql`)."""
    def _rep(m):
        return str(valores.get(m.group(1), m.group(0)))
    return PATRON_VAR.sub(_rep, texto or "")


def preparar_sql(sql: str, valores: dict, marcador="?") -> tuple:
    """Convierte 'WHERE mes = {{mes}}' en ('WHERE mes = ?', ['2026-01']).

    Devuelve (sql_parametrizado, parametros). El valor viaja aparte, así
    que no hay forma de que su contenido se interprete como SQL.
    """
    params = []

    def _rep(m):
        nombre = m.group(1)
        params.append(valores.get(nombre))
        return marcador

    return PATRON_VAR.sub(_rep, sql or ""), params


def faltan_variables(cuaderno: dict, valores: dict) -> list:
    """Variables del cuaderno que no tienen valor asignado."""
    return [v for v in variables_del_cuaderno(cuaderno)
            if valores.get(v) in (None, "")]


# ──────────────────────────────────────────────────────────────
# CRUD de cuadernos
# ──────────────────────────────────────────────────────────────
def listar() -> list:
    return _cargar()


def obtener(nombre: str):
    for c in _cargar():
        if c["nombre"].lower() == (nombre or "").lower():
            return c
    return None


def guardar(nombre: str, celdas: list, descripcion="", valores=None) -> dict:
    """Crea o reemplaza un cuaderno."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El cuaderno necesita un nombre.")
    for i, c in enumerate(celdas or [], 1):
        if c.get("tipo") not in TIPOS_CELDA:
            raise ValueError(f"Celda {i}: tipo inválido ({c.get('tipo')}).")

    items = [c for c in _cargar() if c["nombre"].lower() != nombre.lower()]
    cuaderno = {
        "nombre": nombre,
        "descripcion": descripcion or "",
        "celdas": celdas or [],
        "valores": valores or {},
        "actualizado": datetime.now().isoformat(timespec="seconds"),
    }
    items.append(cuaderno)
    _persistir(items)
    return cuaderno


def eliminar(nombre: str) -> None:
    _persistir([c for c in _cargar()
                if c["nombre"].lower() != (nombre or "").lower()])


def nueva_celda(tipo="markdown", contenido="") -> dict:
    if tipo not in TIPOS_CELDA:
        raise ValueError(f"Tipo de celda inválido: {tipo}")
    return {"tipo": tipo, "contenido": contenido}


def mover_celda(cuaderno: dict, indice: int, delta: int) -> dict:
    """Sube (-1) o baja (+1) una celda. Fuera de rango no hace nada."""
    celdas = cuaderno.get("celdas", [])
    destino = indice + delta
    if 0 <= indice < len(celdas) and 0 <= destino < len(celdas):
        celdas[indice], celdas[destino] = celdas[destino], celdas[indice]
    return cuaderno


# ──────────────────────────────────────────────────────────────
# Exportación del cuaderno completo
# ──────────────────────────────────────────────────────────────
def a_markdown(cuaderno: dict, valores=None, resultados=None) -> str:
    """El cuaderno como documento Markdown, con las variables aplicadas.

    `resultados` es un dict {indice_celda: DataFrame} para incrustar las
    tablas ya calculadas.
    """
    valores = valores or cuaderno.get("valores", {})
    resultados = resultados or {}
    partes = [f"# {cuaderno['nombre']}"]
    if cuaderno.get("descripcion"):
        partes.append(sustituir_texto(cuaderno["descripcion"], valores))
    if valores:
        partes.append("> " + " · ".join(f"**{k}**: {v}" for k, v in valores.items()))

    for i, celda in enumerate(cuaderno.get("celdas", [])):
        contenido = sustituir_texto(celda.get("contenido", ""), valores)
        if celda["tipo"] == "markdown":
            partes.append(contenido)
        elif celda["tipo"] == "pregunta":
            partes.append(f"**Pregunta:** {contenido}")
        else:
            partes.append(f"```sql\n{contenido}\n```")
        df = resultados.get(i)
        if df is not None and hasattr(df, "to_markdown"):
            try:
                partes.append(df.to_markdown(index=False))
            except Exception:
                partes.append(df.to_string(index=False))

    partes.append(f"\n---\n*Generado con MV SQL NLP · "
                  f"{datetime.now().strftime('%d/%m/%Y %H:%M')}*")
    return "\n\n".join(partes)
