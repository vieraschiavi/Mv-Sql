# © 2026 Martín Viera. Todos los derechos reservados.
"""
tablas_externas.py — tablas que trae otro programa (Analysis Services, el MDW) como base consultable
====================================================================================================
Azure Analysis Services (el MDW) no habla SQL: habla DAX. MV SQL NLP genera y
valida SQL, así que no se le puede «conectar» como a SQL Server. Lo que sí se
puede, y es lo que hace la suite Adium All in One, es LEER las tablas del
modelo (con su usuario, en solo lectura) y pasárselas a MV SQL NLP. Acá esas
tablas se vuelcan a una base SQLite temporal —igual que un Excel subido— y
desde ahí todo funciona: catálogo, validación anti-alucinación y SOLO LECTURA.

El que trae las tablas las deja en la sesión, en `CLAVE`:

    estado[CLAVE] = {"etiqueta": "Analysis Services · servidor/modelo",
                     "tablas": {"Venta": DataFrame, ...},
                     "ident": "algo que cambia cuando cambian las tablas"}

y la app las toma una sola vez por `ident` (`pendiente`).
"""
import hashlib
import os
import re
import sqlite3
import tempfile

CLAVE = "mvsql_tablas_externas"
_ULTIMA = "_mvsql_ultima_externa"


def _nombre(texto, i, prefijo):
    n = re.sub(r"\W+", "_", str(texto)).strip("_")
    return n or f"{prefijo}{i}"


def a_sqlite(tablas):
    """Vuelca {nombre: DataFrame} a una base SQLite temporal y devuelve la ruta. Mismas tablas → misma base."""
    if not tablas:
        raise ValueError("No llegó ninguna tabla.")
    firma = hashlib.sha1()
    for n, df in sorted(tablas.items(), key=lambda kv: str(kv[0])):
        firma.update(f"{n}|{list(df.columns)}|{len(df)}".encode())
        firma.update(df.head(50).to_csv(index=False).encode())
    ruta = os.path.join(tempfile.gettempdir(), f"mvsql_externa_{firma.hexdigest()[:12]}.db")
    if os.path.exists(ruta):
        return ruta
    tmp = ruta + ".tmp"
    con = sqlite3.connect(tmp)
    try:
        usados = set()
        for i, (n, df) in enumerate(tablas.items(), 1):
            tabla = _nombre(n, i, "tabla").lower()
            while tabla in usados:
                tabla += "_2"
            usados.add(tabla)
            df = df.copy()
            df.columns = [_nombre(c, j, "col") for j, c in enumerate(df.columns, 1)]
            df.to_sql(tabla, con, index=False, if_exists="replace")
        con.commit()
    finally:
        con.close()
    os.replace(tmp, ruta)
    return ruta


def pendiente(estado):
    """Lo que trajo otro programa y todavía no se aplicó, o None."""
    paquete = estado.get(CLAVE)
    if not paquete or not paquete.get("tablas"):
        return None
    ident = str(paquete.get("ident") or paquete.get("etiqueta") or "")
    if estado.get(_ULTIMA) == ident:
        return None
    return paquete


def marcar_aplicada(estado, paquete):
    estado[_ULTIMA] = str(paquete.get("ident") or paquete.get("etiqueta") or "")


def hay(estado):
    paquete = estado.get(CLAVE)
    return bool(paquete and paquete.get("tablas"))
