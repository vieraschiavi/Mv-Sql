"""
equipo.py — MV SQL NLP
==================================================================
Usuarios, roles y permisos.

Esto es lo que separa a MV SQL NLP de conectar Claude a la base por
MCP: con MCP, cualquiera que tenga la credencial ve TODA la base y no
queda registro de nada. Acá cada persona entra con su usuario, ve solo
las tablas que le corresponden, y todo lo que consulta queda auditado.

Sin equipo configurado la app funciona igual que siempre (un solo
usuario, acceso total): la seguridad se activa cuando hace falta, no
molesta al que la instala para probar.

El archivo equipo.json vive junto a la app. Los PIN se guardan
hasheados con PBKDF2-SHA256 y sal por usuario — nunca en texto plano.
==================================================================
"""

import hashlib
import json
import os
import secrets
from datetime import datetime

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "equipo.json")

# Permisos de cada rol. `tablas` con "*" significa todas.
ROLES = {
    "admin": {
        "nombre": "Administrador",
        "descripcion": "Acceso total. Gestiona el equipo y ve la auditoría.",
        "tablas": "*", "limite_filas": 100000,
        "puede_exportar": True, "puede_sp": True, "ve_auditoria": True,
        "gestiona_equipo": True,
    },
    "analista": {
        "nombre": "Analista",
        "descripcion": "Consulta y exporta las tablas asignadas.",
        "tablas": "*", "limite_filas": 20000,
        "puede_exportar": True, "puede_sp": True, "ve_auditoria": False,
        "gestiona_equipo": False,
    },
    "lector": {
        "nombre": "Lector",
        "descripcion": "Solo consulta. No exporta ni genera procedures.",
        "tablas": "*", "limite_filas": 2000,
        "puede_exportar": False, "puede_sp": False, "ve_auditoria": False,
        "gestiona_equipo": False,
    },
}

ITERACIONES = 120_000


def _hash_pin(pin: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(sal),
                               ITERACIONES).hex()


def cargar() -> dict:
    """Configuración del equipo. Si no existe, equipo vacío (modo abierto)."""
    if not os.path.exists(RUTA):
        return {"activo": False, "usuarios": []}
    try:
        with open(RUTA, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.setdefault("activo", False)
        cfg.setdefault("usuarios", [])
        return cfg
    except (json.JSONDecodeError, OSError):
        return {"activo": False, "usuarios": []}


def guardar(cfg: dict) -> None:
    tmp = RUTA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, RUTA)


def crear_usuario(nombre: str, rol: str, pin: str, tablas=None) -> dict:
    """Agrega un usuario. `tablas`=None hereda las del rol."""
    if rol not in ROLES:
        raise ValueError(f"Rol desconocido: {rol}")
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if not pin or len(str(pin)) < 4:
        raise ValueError("El PIN debe tener al menos 4 dígitos.")

    cfg = cargar()
    if any(u["nombre"].lower() == nombre.lower() for u in cfg["usuarios"]):
        raise ValueError(f"Ya existe un usuario llamado {nombre}.")

    sal = secrets.token_hex(16)
    usuario = {
        "nombre": nombre, "rol": rol, "sal": sal, "pin": _hash_pin(str(pin), sal),
        "tablas": tablas if tablas is not None else ROLES[rol]["tablas"],
        "creado": datetime.now().isoformat(timespec="seconds"),
    }
    cfg["usuarios"].append(usuario)
    cfg["activo"] = True          # con el primer usuario se activa el control
    guardar(cfg)
    return usuario


def eliminar_usuario(nombre: str) -> None:
    cfg = cargar()
    quedan = [u for u in cfg["usuarios"] if u["nombre"].lower() != nombre.lower()]
    # No dejar el equipo sin ningún administrador: sería imposible volver a entrar.
    if quedan and not any(u["rol"] == "admin" for u in quedan):
        raise ValueError("No podés eliminar al último administrador.")
    cfg["usuarios"] = quedan
    if not quedan:
        cfg["activo"] = False     # sin usuarios, vuelve al modo abierto
    guardar(cfg)


def autenticar(nombre: str, pin: str):
    """Devuelve el usuario si el PIN es correcto, si no None."""
    for u in cargar()["usuarios"]:
        if u["nombre"].lower() == (nombre or "").lower():
            esperado = u["pin"]
            calculado = _hash_pin(str(pin), u["sal"])
            # comparación en tiempo constante: no filtra el PIN por timing
            if secrets.compare_digest(esperado, calculado):
                return u
            return None
    return None


def permisos(usuario) -> dict:
    """Permisos efectivos. Sin usuario (modo abierto) = acceso total."""
    if not usuario:
        return dict(ROLES["admin"], tablas="*", rol="admin", nombre_usuario="")
    base = dict(ROLES.get(usuario["rol"], ROLES["lector"]))
    base["tablas"] = usuario.get("tablas", base["tablas"])
    base["rol"] = usuario["rol"]
    base["nombre_usuario"] = usuario["nombre"]
    return base


def tablas_visibles(catalogo: dict, perm: dict) -> dict:
    """Recorta el catálogo del esquema a lo que el usuario puede ver.

    Es la defensa real: si la tabla no está en el catálogo, la IA nunca
    se entera de que existe y no puede generar SQL contra ella.
    """
    if perm.get("tablas") == "*":
        return catalogo
    permitidas = {t.lower() for t in perm.get("tablas", [])}
    filtrado = dict(catalogo)
    filtrado["tablas"] = {k: v for k, v in catalogo.get("tablas", {}).items()
                          if k.lower() in permitidas}
    return filtrado


def puede_consultar_tablas(tablas_usadas, perm: dict) -> tuple:
    """(permitido, tablas_prohibidas) para el SQL ya generado."""
    if perm.get("tablas") == "*":
        return True, []
    permitidas = {t.lower() for t in perm.get("tablas", [])}
    prohibidas = [t for t in tablas_usadas if t.lower() not in permitidas]
    return (not prohibidas), prohibidas
