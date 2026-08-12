# app-python/motor.py

- RecuperadorEsquema · class · L29-L42 — class RecuperadorEsquema
- __init__ · method · L30-L35 — def __init__(self, fichas)
- recuperar · method · L37-L42 — def recuperar(self, pregunta, k=4)
- _parsear_respuesta_sql · function · L60-L83 — def _parsear_respuesta_sql(texto)
- validar_sql · function · L100-L134 — def validar_sql(sql, catalogo, ctes=None)
- calcular_confianza · function · L140-L177 — def calcular_confianza(conf_llm, sim_rag, es_valido, n_advertencias, usa_cte)
- MotorMVSQL · class · L183-L360 — class MotorMVSQL
- __init__ · method · L189-L198 — def __init__(self, conexion, ia)
- _completar · method · L200-L203 — def _completar(self, system, user, max_tokens=1500)
- responder · method · L205-L300 — def responder(self, pregunta, k=4, limite=5000, explicar=True, contexto="", privado=False)
- _reintentar_sql · method · L302-L320 — def _reintentar_sql(self, system, pregunta_ia, sql, problemas)
- _explicar_resultado · method · L322-L341 — def _explicar_resultado(self, pregunta, sql, resultado, contexto)
- generar_stored_procedure · method · L343-L352 — def generar_stored_procedure(self, sql, nombre="sp_mvsql_consulta")
- optimizar_sql · method · L354-L360 — def optimizar_sql(self, sql)
- _muestra_texto · function · L363-L369 — def _muestra_texto(cols, filas, max_filas=20)
