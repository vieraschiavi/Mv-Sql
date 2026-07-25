"""
sembrar_demo.py — datos de escenografía para el video.
==================================================================
Crea el equipo, la auditoría y la licencia de créditos que se ven en
cámara. Sin esto la app se muestra vacía ("todavía no creaste…") y el
video parece una instalación recién bajada, no un producto en uso.

Nada de esto se versiona: equipo.json, auditoria.db y
licencia_mvsql.json están en .gitignore.

    python tools/video/sembrar_demo.py
==================================================================
"""

import json
import os
import sys
from datetime import datetime, timedelta

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "..", "..", "app-python"))
sys.path.insert(0, APP)

import auditoria  # noqa: E402
import equipo  # noqa: E402

PIN_ADMIN = "2468"

EQUIPO = [
    # (nombre, rol, pin, tablas visibles)
    ("Martín", "admin", PIN_ADMIN, None),
    ("Ana", "analista", "1357", ["clientes", "operaciones", "cuotas", "arreglos_pago"]),
    ("Diego", "lector", "1122", ["gestiones", "estados_cliente"]),
]

HISTORIAL = [
    ("Martín", "admin", "¿Cuánto cobramos por mes en 2026?", 6, "ok"),
    ("Ana", "analista", "Top 10 clientes con más deuda en estado jurídico", 10, "ok"),
    ("Ana", "analista", "Contactabilidad por gestor", 14, "ok"),
    ("Diego", "lector", "Gestiones por canal en el último trimestre", 8, "ok"),
    ("Diego", "lector", "Sueldos por sucursal", 0, "rechazado"),
]


def main():
    for ruta in (equipo.RUTA, os.path.join(APP, "licencia_mvsql.json")):
        if os.path.exists(ruta):
            os.remove(ruta)

    for nombre, rol, pin, tablas in EQUIPO:
        equipo.crear_usuario(nombre, rol, pin, tablas=tablas)
    print(f"✓ equipo: {', '.join(u for u, _, _, _ in EQUIPO)}")

    base = datetime.now() - timedelta(days=3)
    for i, (usuario, rol, pregunta, filas, resultado) in enumerate(HISTORIAL):
        auditoria.registrar(usuario=usuario, rol=rol, pregunta=pregunta,
                            sql="SELECT …", filas=filas, resultado=resultado,
                            detalle="" if resultado == "ok" else "tabla fuera de su rol")
    print(f"✓ auditoría: {len(HISTORIAL)} consultas registradas")

    licencia = {"email": "demo@mvsqlnlp.com", "plan": "Demo",
                "creditos": 500, "vence": "2027-12-31T00:00:00Z",
                "jti": "demo-video"}
    with open(os.path.join(APP, "licencia_mvsql.json"), "w", encoding="utf-8") as fh:
        json.dump(licencia, fh, ensure_ascii=False, indent=2)
    print("✓ licencia de créditos (para que no salga el aviso en cámara)")
    print(f"\nPIN del admin para la captura: {PIN_ADMIN}")


if __name__ == "__main__":
    main()
