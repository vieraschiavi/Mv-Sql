"""
guardadas.py — MV SQL NLP
==================================================================
Biblioteca de consultas guardadas con nombre, descripción y etiquetas.
Se persisten en un JSON local del usuario (no requiere servidor).
Desde una consulta guardada se puede regenerar el resultado o
convertirla en stored procedure.
==================================================================
"""

import json
import os
from datetime import datetime

ARCHIVO_DEFAULT = os.path.join(os.path.expanduser("~"), ".mvsql", "consultas_guardadas.json")


def _cargar(archivo=ARCHIVO_DEFAULT):
    if not os.path.exists(archivo):
        return []
    try:
        with open(archivo, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _persistir(items, archivo=ARCHIVO_DEFAULT):
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def listar(archivo=ARCHIVO_DEFAULT):
    return _cargar(archivo)


def guardar(nombre, pregunta, sql, dialecto="", etiquetas=None,
            descripcion="", archivo=ARCHIVO_DEFAULT):
    """Guarda o actualiza (por nombre) una consulta."""
    items = _cargar(archivo)
    nueva = {
        "nombre": nombre.strip(),
        "descripcion": descripcion.strip(),
        "pregunta": pregunta,
        "sql": sql,
        "dialecto": dialecto,
        "etiquetas": etiquetas or [],
        "actualizada": datetime.now().isoformat(timespec="seconds"),
    }
    for i, it in enumerate(items):
        if it["nombre"].lower() == nueva["nombre"].lower():
            nueva.setdefault("creada", it.get("creada", nueva["actualizada"]))
            items[i] = nueva
            _persistir(items, archivo)
            return nueva
    nueva["creada"] = nueva["actualizada"]
    items.append(nueva)
    _persistir(items, archivo)
    return nueva


def eliminar(nombre, archivo=ARCHIVO_DEFAULT):
    items = _cargar(archivo)
    filtradas = [it for it in items if it["nombre"].lower() != nombre.lower()]
    _persistir(filtradas, archivo)
    return len(items) - len(filtradas)


def buscar(texto, archivo=ARCHIVO_DEFAULT):
    t = texto.lower()
    return [it for it in _cargar(archivo)
            if t in it["nombre"].lower() or t in it.get("pregunta", "").lower()
            or any(t in e.lower() for e in it.get("etiquetas", []))]
