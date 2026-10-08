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

La suite manda además, opcionales:

    "conocimiento": texto con definiciones del negocio (mercados conformados,
                    glosario): va al prompt, no son datos de la base;
    "relaciones":   [{"tabla_origen", "columna_origen", "tabla_destino",
                    "columna_destino"}] del modelo, con los nombres de allá;
    "tablas_clave": tablas que se le muestran a la IA siempre que la pregunta
                    hable de mercado o share, aunque el buscador no las elija.

`contexto()` los traduce a los nombres que tienen en la base SQLite.
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


def nombres(tablas):
    """{nombre original: (nombre en SQLite, {columna original: columna en SQLite})}, como los escribe `a_sqlite`."""
    salida, usados = {}, set()
    for i, (n, df) in enumerate(tablas.items(), 1):
        tabla = _nombre(n, i, "tabla").lower()
        while tabla in usados:
            tabla += "_2"
        usados.add(tabla)
        salida[n] = (tabla, {c: _nombre(c, j, "col") for j, c in enumerate(df.columns, 1)})
    return salida


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
        for n, (tabla, cols) in nombres(tablas).items():
            df = tablas[n].copy()
            df.columns = [cols[c] for c in df.columns]
            df.to_sql(tabla, con, index=False, if_exists="replace")
        con.commit()
    finally:
        con.close()
    os.replace(tmp, ruta)
    return ruta


def _buscar(dic, clave):
    """La entrada de `dic` cuya clave coincide con `clave` sin mirar mayúsculas (la suite y el modelo no siempre
    escriben igual una tabla), o None."""
    if clave in dic:
        return dic[clave]
    bajo = str(clave).lower()
    return next((v for k, v in dic.items() if str(k).lower() == bajo), None)


def contexto(paquete):
    """(conocimiento, relaciones, tablas_clave) del paquete, con los nombres que tienen en la base SQLite.

    Una relación que nombra una tabla o columna que no vino se descarta: un JOIN
    contra algo que no existe lo frenaría igual la validación, pero antes le
    habría hecho perder el intento a la IA."""
    tablas = paquete.get("tablas") or {}
    mapa = nombres(tablas)
    rels = []
    for r in paquete.get("relaciones") or ():
        try:
            o, d = _buscar(mapa, r["tabla_origen"]), _buscar(mapa, r["tabla_destino"])
            if not (o and d):
                continue
            co, cd = _buscar(o[1], r["columna_origen"]), _buscar(d[1], r["columna_destino"])
        except (KeyError, TypeError):
            continue
        if co and cd:
            rels.append({"tabla_origen": o[0], "columna_origen": co, "tabla_destino": d[0], "columna_destino": cd})
    clave = [m[0] for m in (_buscar(mapa, n) for n in paquete.get("tablas_clave") or ()) if m]
    return str(paquete.get("conocimiento") or ""), rels, clave


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
