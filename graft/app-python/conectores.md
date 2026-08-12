# app-python/conectores.py

- SQLNoPermitido · class · L27-L28 — class SQLNoPermitido(Exception)
- _sin_comentarios · function · L79-L80 — def _sin_comentarios(sql)
- _sin_literales · function · L83-L84 — def _sin_literales(sql)
- asegurar_solo_lectura · function · L87-L124 — def asegurar_solo_lectura(sql)
- ConexionBD · class · L134-L305 — class ConexionBD
- __init__ · method · L137-L151 — def __init__(self, motor, ruta=None, servidor=None, puerto=None, base=None, usuario=None, password=None, driver=None, ssh=None)
- _abrir_tunel · method · L154-L189 — def _abrir_tunel(self)
- conectar · method · L192-L247 — def conectar(self)
- cerrar · method · L249-L261 — def cerrar(self)
- extraer_catalogo · method · L264-L272 — def extraer_catalogo(self)
- marcador_param · method · L276-L278 — def marcador_param(self)
- ejecutar · method · L280-L305 — def ejecutar(self, sql, limite=5000, params=None)
- _aplicar_limite · function · L308-L319 — def _aplicar_limite(sql, dialecto, limite)
- _extraer_catalogo_information_schema · function · L322-L406 — def _extraer_catalogo_information_schema(con, motor, base)
