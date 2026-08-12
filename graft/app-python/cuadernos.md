# app-python/cuadernos.py

- _cargar · function · L35-L43 — def _cargar()
- _persistir · function · L46-L51 — def _persistir(items)
- variables_usadas · function · L57-L64 — def variables_usadas(texto: str) -> list
- variables_del_cuaderno · function · L67-L75 — def variables_del_cuaderno(cuaderno: dict) -> list
- sustituir_texto · function · L78-L83 — def sustituir_texto(texto: str, valores: dict) -> str
- _rep · function · L81-L82 — def _rep(m)
- preparar_sql · function · L86-L99 — def preparar_sql(sql: str, valores: dict, marcador="?") -> tuple
- _rep · function · L94-L97 — def _rep(m)
- faltan_variables · function · L102-L105 — def faltan_variables(cuaderno: dict, valores: dict) -> list
- listar · function · L111-L112 — def listar() -> list
- obtener · function · L115-L119 — def obtener(nombre: str)
- guardar · function · L122-L141 — def guardar(nombre: str, celdas: list, descripcion="", valores=None) -> dict
- eliminar · function · L144-L146 — def eliminar(nombre: str) -> None
- nueva_celda · function · L149-L152 — def nueva_celda(tipo="markdown", contenido="") -> dict
- mover_celda · function · L155-L161 — def mover_celda(cuaderno: dict, indice: int, delta: int) -> dict
- a_markdown · function · L167-L198 — def a_markdown(cuaderno: dict, valores=None, resultados=None) -> str
