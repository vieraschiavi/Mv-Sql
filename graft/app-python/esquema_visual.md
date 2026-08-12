# app-python/esquema_visual.py

- diagrama_mermaid · function · L24-L62 — def diagrama_mermaid(catalogo: dict, tablas=None, max_columnas=8) -> str
- _id_mermaid · function · L65-L68 — def _id_mermaid(nombre: str) -> str
- _tipo_corto · function · L71-L83 — def _tipo_corto(tipo: str) -> str
- resumen_relaciones · function · L86-L92 — def resumen_relaciones(catalogo: dict) -> list
- tablas_sin_relacion · function · L95-L102 — def tablas_sin_relacion(catalogo: dict) -> list
- plan_de_ejecucion · function · L142-L177 — def plan_de_ejecucion(conexion, sql: str)
- costo_estimado · function · L180-L190 — def costo_estimado(filas_plan) -> str
- diagrama_dot · function · L193-L244 — def diagrama_dot(catalogo: dict, tablas=None, max_columnas=8) -> str
- _escapar · function · L247-L250 — def _escapar(texto: str) -> str
