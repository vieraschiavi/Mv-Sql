# app-python/equipo.py

- _hash_pin · function · L57-L59 — def _hash_pin(pin: str, sal: str) -> str
- cargar · function · L62-L73 — def cargar() -> dict
- guardar · function · L76-L80 — def guardar(cfg: dict) -> None
- crear_usuario · function · L83-L114 — def crear_usuario(nombre: str, rol: str, pin: str, tablas=None) -> dict
- eliminar_usuario · function · L117-L126 — def eliminar_usuario(nombre: str) -> None
- autenticar · function · L129-L139 — def autenticar(nombre: str, pin: str)
- permisos · function · L142-L150 — def permisos(usuario) -> dict
- tablas_visibles · function · L153-L184 — def tablas_visibles(catalogo: dict, perm: dict) -> dict
- _ok · function · L170-L172 — def _ok(fk)
- puede_consultar_tablas · function · L187-L193 — def puede_consultar_tablas(tablas_usadas, perm: dict) -> tuple
- tablas_en_sql · function · L202-L219 — def tablas_en_sql(sql: str) -> list
- puede_consultar_sql · function · L222-L229 — def puede_consultar_sql(sql: str, perm: dict) -> tuple
