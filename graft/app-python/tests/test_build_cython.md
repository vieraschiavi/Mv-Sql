# app-python/tests/test_build_cython.py

- test · function · L31-L41 — def test(nombre)
- deco · function · L32-L40 — def deco(fn)
- _correr · function · L44-L53 — def _correr(*args, encoding="cp1252")
- _ · function · L60-L61 — def _()
- _ · function · L65-L92 — def _(): # Este es EL caso que rompio el release. No alcanza con correr # --limpiar: sus mensajes son ASCII y pasan igual sin el arreglo, o # sea que ese test daria verde con el bug puesto. Hay que ejercitar el # print de _compilar(), que es el que tiene el "check". # # Importar el modulo alcanza y no compila nada: _compilar() esta detras # de if __name__ == "__main__". Lo que se busca del import es su efecto # al cargarse — dejar stdout en UTF-8.
- _ · function · L96-L99 — def _()
- _ · function · L103-L109 — def _(): # El mensaje de "falta Cython" sale por stderr. Si solo se reconfigura # stdout, ese camino sigue explotando — y es justo el que ve alguien # que corre el script sin las dependencias puestas.
- _ · function · L113-L115 — def _()
