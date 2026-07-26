"""
app_demo.py — la app real, con la IA simulada.
==================================================================
Para grabar el video no se puede depender de una API key ni de que
el proveedor conteste igual dos veces. Esto corre la app tal cual
está en app-python/app.py, pero reemplaza la llamada a la IA por una
respuesta fija y correcta.

Es solo para grabar: no se empaqueta ni se distribuye.

    streamlit run tools/video/app_demo.py -- --server.port 8899
==================================================================
"""

import os
import sys

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app-python")
APP = os.path.abspath(APP)
sys.path.insert(0, APP)
os.chdir(APP)

import proveedores_ia  # noqa: E402

SQL_DEMO = """WITH cobros AS (
    SELECT strftime('%Y-%m', c.fecha_cobro) AS mes,
           c.monto + c.punitorios          AS cobrado
    FROM cuotas c
    WHERE c.fecha_cobro IS NOT NULL
      AND c.anulada = 0
      AND c.fecha_cobro >= '2026-01-01'
)
SELECT mes,
       COUNT(*)      AS cuotas_cobradas,
       SUM(cobrado)  AS total_cobrado
FROM cobros
GROUP BY mes
ORDER BY mes"""

EXPLICACION = {
    "es": ("En 2026 se cobraron 12.470 cuotas por un total de $U 41,3 millones. "
           "El mejor mes fue marzo, con $U 6,1 millones, y el más flojo enero, "
           "con $U 3,2 millones: la diferencia es de casi el doble. "
           "El promedio mensual se ubica en $U 4,6 millones."),
    "en": ("In 2026, 12,470 instalments were collected for a total of $U 41.3 "
           "million. March was the strongest month at $U 6.1 million and January "
           "the weakest at $U 3.2 million — almost double the gap. "
           "The monthly average sits at $U 4.6 million."),
    "pt": ("Em 2026 foram recebidas 12.470 parcelas, num total de $U 41,3 "
           "milhões. Março foi o melhor mês, com $U 6,1 milhões, e janeiro o mais "
           "fraco, com $U 3,2 milhões: quase o dobro de diferença. "
           "A média mensal fica em $U 4,6 milhões."),
}


def _idioma(texto):
    """Adivina el idioma de la pregunta para contestar en el mismo."""
    t = (texto or "").lower()
    if any(p in t for p in ("quanto", "quantas", "mês", "por mês", "gestor (%",
                            "operações", "dívida")):
        return "pt"
    if any(p in t for p in ("monthly", "how much", "clients", "operations per",
                            "contact rate")):
        return "en"
    return "es"


def _fingir(proveedor, api_key, system, user, modelo=None, max_tokens=1500,
            base_url=None, **kw):
    if "analista de datos" in (system or "").lower() or "PREGUNTA:" in (user or ""):
        return EXPLICACION[_idioma(user)]
    return f"SQL:\n{SQL_DEMO}\n\nCONFIANZA: 93\nSUPUESTOS: ninguno"


proveedores_ia.completar = _fingir

with open(os.path.join(APP, "app.py"), encoding="utf-8") as fh:
    codigo = fh.read()

exec(compile(codigo, os.path.join(APP, "app.py"), "exec"), {"__name__": "__main__"})
