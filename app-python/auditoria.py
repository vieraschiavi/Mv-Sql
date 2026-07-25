"""
auditoria.py — MV SQL NLP
==================================================================
Registro de quién consultó qué, cuándo y con qué resultado.

El otro motivo por el que una empresa paga esto en vez de conectar
Claude por MCP: cuando el auditor, el oficial de cumplimiento o el
dueño pregunta "¿quién sacó esta información y cuándo?", hay una
respuesta. Con MCP no queda rastro de nada.

Se guarda en SQLite local (auditoria.db), junto a la app. No sale de
la máquina: el registro es tan privado como los datos.
==================================================================
"""

import os
import sqlite3
from datetime import datetime, timedelta

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auditoria.db")

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS consultas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT    NOT NULL,
    usuario     TEXT    NOT NULL,
    rol         TEXT,
    pregunta    TEXT,
    sql         TEXT,
    tablas      TEXT,
    filas       INTEGER,
    confianza   INTEGER,
    resultado   TEXT    NOT NULL,   -- ok | rechazado | error
    detalle     TEXT
);
CREATE INDEX IF NOT EXISTS ix_consultas_fecha   ON consultas(fecha);
CREATE INDEX IF NOT EXISTS ix_consultas_usuario ON consultas(usuario);
"""


def _con():
    con = sqlite3.connect(RUTA)
    con.executescript(_ESQUEMA)
    return con


def registrar(usuario="(sin usuario)", rol="", pregunta="", sql="", tablas=None,
              filas=None, confianza=None, resultado="ok", detalle=""):
    """Deja constancia de una consulta. Nunca interrumpe la app si falla."""
    try:
        with _con() as con:
            con.execute(
                "INSERT INTO consultas (fecha, usuario, rol, pregunta, sql, tablas,"
                " filas, confianza, resultado, detalle) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), usuario or "(sin usuario)",
                 rol or "", (pregunta or "")[:2000], (sql or "")[:8000],
                 ", ".join(tablas or []), filas, confianza, resultado,
                 (detalle or "")[:1000]),
            )
    except sqlite3.Error:
        pass


def listar(limite=200, usuario=None, desde_dias=None):
    """Últimas consultas, la más reciente primero."""
    q = ("SELECT fecha, usuario, rol, pregunta, sql, tablas, filas, confianza,"
         " resultado, detalle FROM consultas WHERE 1=1")
    params = []
    if usuario:
        q += " AND usuario = ?"
        params.append(usuario)
    if desde_dias:
        corte = (datetime.now() - timedelta(days=int(desde_dias))).isoformat()
        q += " AND fecha >= ?"
        params.append(corte)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(int(limite))
    try:
        with _con() as con:
            cur = con.execute(q, params)
            cols = [d[0] for d in cur.description]
            return cols, cur.fetchall()
    except sqlite3.Error:
        return [], []


def resumen(desde_dias=30):
    """KPIs para el panel: total, por usuario, rechazos y confianza media."""
    corte = (datetime.now() - timedelta(days=int(desde_dias))).isoformat()
    vacio = {"total": 0, "por_usuario": [], "rechazadas": 0, "errores": 0,
             "confianza_media": None, "tablas_top": []}
    try:
        with _con() as con:
            total = con.execute(
                "SELECT COUNT(*) FROM consultas WHERE fecha >= ?", (corte,)).fetchone()[0]
            if not total:
                return vacio
            por_usuario = con.execute(
                "SELECT usuario, COUNT(*) n FROM consultas WHERE fecha >= ?"
                " GROUP BY usuario ORDER BY n DESC", (corte,)).fetchall()
            rechazadas = con.execute(
                "SELECT COUNT(*) FROM consultas WHERE fecha >= ? AND resultado = 'rechazado'",
                (corte,)).fetchone()[0]
            errores = con.execute(
                "SELECT COUNT(*) FROM consultas WHERE fecha >= ? AND resultado = 'error'",
                (corte,)).fetchone()[0]
            conf = con.execute(
                "SELECT AVG(confianza) FROM consultas WHERE fecha >= ? AND confianza IS NOT NULL",
                (corte,)).fetchone()[0]
            filas_tablas = con.execute(
                "SELECT tablas FROM consultas WHERE fecha >= ? AND tablas <> ''",
                (corte,)).fetchall()
    except sqlite3.Error:
        return vacio

    conteo = {}
    for (txt,) in filas_tablas:
        for t in (x.strip() for x in txt.split(",") if x.strip()):
            conteo[t] = conteo.get(t, 0) + 1
    top = sorted(conteo.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {"total": total, "por_usuario": por_usuario, "rechazadas": rechazadas,
            "errores": errores,
            "confianza_media": round(conf) if conf is not None else None,
            "tablas_top": top}


def a_csv(limite=5000):
    """Registro completo en CSV, para entregar a auditoría o cumplimiento."""
    import csv
    import io

    cols, filas = listar(limite=limite)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cols or ["fecha", "usuario", "rol", "pregunta", "sql", "tablas",
                        "filas", "confianza", "resultado", "detalle"])
    w.writerows(filas)
    return buf.getvalue().encode("utf-8-sig")
