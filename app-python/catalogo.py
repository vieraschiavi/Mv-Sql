"""
catalogo.py
==================================================================
Extrae el catalogo completo de una base de datos (el "esquema") para
alimentar el RAG. Funciona con SQLite (demo) y SQL Server (produccion).

Esto es el equivalente Python del query EXTRAER_METADATA_BD_COMPLETA.sql:
genera, por cada tabla, una "ficha" en lenguaje natural que el sistema
RAG indexa. Cuando llega una pregunta, se recuperan las fichas mas
relevantes y se le pasan al LLM como contexto -> SQL sin nombres inventados.
==================================================================
"""

import sqlite3
import json


# ──────────────────────────────────────────────────────────────
# EXTRACCION SQLITE (demo)
# ──────────────────────────────────────────────────────────────
def extraer_catalogo_sqlite(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Lista de tablas
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tablas = [r[0] for r in cur.fetchall()]

    catalogo = {"tablas": {}, "fks": [], "joins_inferidos": {}}

    # Columnas por tabla + conteo de filas
    columnas_por_tabla = {}
    for t in tablas:
        cur.execute(f"PRAGMA table_info({t})")
        cols = []
        for cid, name, tipo, notnull, default, pk in cur.fetchall():
            cols.append({
                "columna": name, "tipo": tipo or "TEXT",
                "nullable": not notnull, "pk": bool(pk)
            })
        columnas_por_tabla[t] = [c["columna"] for c in cols]

        cur.execute(f"SELECT COUNT(*) FROM {t}")
        n_filas = cur.fetchone()[0]

        # muestra de valores para columnas de texto (ayuda al LLM a entender dominios)
        muestras = {}
        for c in cols:
            if c["tipo"].upper() in ("TEXT", "VARCHAR") and not c["pk"]:
                try:
                    cur.execute(f"SELECT DISTINCT {c['columna']} FROM {t} "
                                f"WHERE {c['columna']} IS NOT NULL LIMIT 8")
                    vals = [r[0] for r in cur.fetchall()]
                    if vals and len(vals) <= 8:
                        muestras[c["columna"]] = vals
                except Exception:
                    pass

        catalogo["tablas"][t] = {
            "columnas": cols, "n_filas": n_filas, "muestras": muestras
        }

    # FKs declaradas
    for t in tablas:
        cur.execute(f"PRAGMA foreign_key_list({t})")
        for row in cur.fetchall():
            # row: id, seq, table, from, to, on_update, on_delete, match
            catalogo["fks"].append({
                "tabla_origen": t, "columna_origen": row[3],
                "tabla_destino": row[2], "columna_destino": row[4]
            })

    # Joins inferidos por nombre de columna (relaciones no declaradas)
    col_a_tablas = {}
    for t, cols in columnas_por_tabla.items():
        for c in cols:
            if c.lower().endswith("_id") or c.lower().startswith("id"):
                col_a_tablas.setdefault(c, []).append(t)
    catalogo["joins_inferidos"] = {
        c: ts for c, ts in col_a_tablas.items() if len(ts) > 1
    }

    con.close()
    return catalogo


# ──────────────────────────────────────────────────────────────
# EXTRACCION SQL SERVER (produccion) — usa sys.* / INFORMATION_SCHEMA
# ──────────────────────────────────────────────────────────────
def extraer_catalogo_mssql(con):
    """
    con: conexion pyodbc ya abierta.
    Replica los result sets del SQL de metadata.
    """
    cur = con.cursor()
    catalogo = {"tablas": {}, "fks": [], "joins_inferidos": {}}

    # Columnas + tipos
    cur.execute("""
        SELECT t.name AS tabla, c.name AS columna, ty.name AS tipo,
               c.is_nullable,
               CASE WHEN pk.column_id IS NOT NULL THEN 1 ELSE 0 END AS es_pk
        FROM sys.columns c
        JOIN sys.tables t  ON t.object_id = c.object_id
        JOIN sys.types ty  ON ty.user_type_id = c.user_type_id
        LEFT JOIN (
            SELECT ic.object_id, ic.column_id FROM sys.index_columns ic
            JOIN sys.indexes i ON i.object_id=ic.object_id AND i.index_id=ic.index_id
            WHERE i.is_primary_key=1
        ) pk ON pk.object_id=c.object_id AND pk.column_id=c.column_id
        ORDER BY t.name, c.column_id
    """)
    columnas_por_tabla = {}
    for tabla, columna, tipo, nullable, es_pk in cur.fetchall():
        catalogo["tablas"].setdefault(tabla, {"columnas": [], "n_filas": None, "muestras": {}})
        catalogo["tablas"][tabla]["columnas"].append({
            "columna": columna, "tipo": tipo, "nullable": bool(nullable), "pk": bool(es_pk)
        })
        columnas_por_tabla.setdefault(tabla, []).append(columna)

    # Conteo de filas
    cur.execute("""
        SELECT t.name, SUM(p.rows)
        FROM sys.tables t
        JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1)
        GROUP BY t.name
    """)
    for tabla, filas in cur.fetchall():
        if tabla in catalogo["tablas"]:
            catalogo["tablas"][tabla]["n_filas"] = int(filas) if filas else 0

    # FKs
    cur.execute("""
        SELECT tp.name, cp.name, tr.name, cr.name
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.tables tp  ON tp.object_id=fkc.parent_object_id
        JOIN sys.columns cp ON cp.object_id=fkc.parent_object_id AND cp.column_id=fkc.parent_column_id
        JOIN sys.tables tr  ON tr.object_id=fkc.referenced_object_id
        JOIN sys.columns cr ON cr.object_id=fkc.referenced_object_id AND cr.column_id=fkc.referenced_column_id
    """)
    for to_, co, td, cd in cur.fetchall():
        catalogo["fks"].append({
            "tabla_origen": to_, "columna_origen": co,
            "tabla_destino": td, "columna_destino": cd
        })

    # Joins inferidos
    col_a_tablas = {}
    for t, cols in columnas_por_tabla.items():
        for c in cols:
            if c.lower().endswith("id") or c.lower().startswith("id") or c.lower().startswith("num"):
                col_a_tablas.setdefault(c, []).append(t)
    catalogo["joins_inferidos"] = {c: ts for c, ts in col_a_tablas.items() if len(ts) > 1}

    return catalogo


# ──────────────────────────────────────────────────────────────
# CONSTRUIR FICHAS DE TEXTO PARA EL RAG (1 ficha por tabla)
# ──────────────────────────────────────────────────────────────
def catalogo_a_fichas(catalogo):
    """
    Convierte el catalogo en una lista de fichas de texto.
    Cada ficha describe una tabla en lenguaje natural -> se embebe para el RAG.
    """
    fichas = []
    for tabla, info in catalogo["tablas"].items():
        lineas = [f"TABLA: {tabla}"]
        if info.get("n_filas") is not None:
            lineas.append(f"Cantidad de filas: {info['n_filas']:,}")

        lineas.append("Columnas:")
        for c in info["columnas"]:
            marca = " [PK]" if c["pk"] else ""
            null = "" if c["nullable"] else " NOT NULL"
            extra = ""
            if c["columna"] in info.get("muestras", {}):
                vals = ", ".join(str(v) for v in info["muestras"][c["columna"]])
                extra = f"  (valores ejemplo: {vals})"
            lineas.append(f"  - {c['columna']} ({c['tipo']}){null}{marca}{extra}")

        # relaciones de esta tabla
        rels = []
        for fk in catalogo["fks"]:
            if fk["tabla_origen"] == tabla:
                rels.append(f"  {tabla}.{fk['columna_origen']} -> "
                            f"{fk['tabla_destino']}.{fk['columna_destino']}")
            if fk["tabla_destino"] == tabla:
                rels.append(f"  {fk['tabla_origen']}.{fk['columna_origen']} -> "
                            f"{tabla}.{fk['columna_destino']}")
        if rels:
            lineas.append("Relaciones (JOINs):")
            lineas.extend(rels)

        fichas.append({"tabla": tabla, "texto": "\n".join(lineas)})

    return fichas


def resumen_esquema_compacto(catalogo):
    """Resumen de 1 linea por tabla — para system prompt cuando son pocas tablas."""
    out = []
    for tabla, info in catalogo["tablas"].items():
        cols = ", ".join(c["columna"] for c in info["columnas"])
        out.append(f"{tabla}({cols})")
    rels = [f"{fk['tabla_origen']}.{fk['columna_origen']}={fk['tabla_destino']}.{fk['columna_destino']}"
            for fk in catalogo["fks"]]
    txt = "TABLAS:\n" + "\n".join(out)
    if rels:
        txt += "\n\nRELACIONES:\n" + "\n".join(rels)
    return txt


if __name__ == "__main__":
    cat = extraer_catalogo_sqlite("cartera_demo.db")
    print(f"Tablas extraidas: {len(cat['tablas'])}")
    print(f"FKs: {len(cat['fks'])}")
    print(f"Joins inferidos: {list(cat['joins_inferidos'].keys())}")
    print("\n--- EJEMPLO DE FICHA ---\n")
    fichas = catalogo_a_fichas(cat)
    print(fichas[1]["texto"])
    # guardar para inspeccion
    with open("catalogo_demo.json", "w") as f:
        json.dump(cat, f, indent=2, ensure_ascii=False)
    print("\nGuardado catalogo_demo.json")
