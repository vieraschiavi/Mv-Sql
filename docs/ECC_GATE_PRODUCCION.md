# MV SQL NLP — Gate de producción ECC

> Puntaje bajo la rúbrica de `.claude/skills/ecc/SKILL.md` (ECC v2.2.0,
> skill `production-audit`). **Evidencia ejecutada o no cuenta.**

**Veredicto: 91/100 → 9/10. Sin bloqueantes. La defensa contra inyección SQL
—que es LA superficie de riesgo de un producto que traduce lenguaje natural a
SQL— está cubierta por test contra una conexión real, no contra un doble.**

## Evidencia ejecutada

| Verificación | Comando | Resultado |
|---|---|---|
| Suite completa (web + app-python) | `npm test` | ✅ **41 archivos, todo en verde** |
| Linter | `npm run lint` | ✅ sin hallazgos |
| Instalación limpia | `npm ci` | ✅ 125 paquetes desde el lockfile |
| Secretos versionados | `git ls-files \| grep -E '\.env$\|\.pem\|\.keystore'` | ✅ ninguno |

## Lo que cubre bien

**Inyección SQL, contra una conexión de verdad.** El bloque "Contra una
conexión de verdad (no solo la función suelta)" prueba que
`ejecutar('DROP TABLE clientes')` no borra la tabla, que el `DELETE` se frena
**antes** de llegar al cursor, que SQLite además abre en modo read-only
(defensa en profundidad), y que las variables del cuaderno viajan como
parámetros y no concatenadas. Para un producto cuyo trabajo es convertir
lenguaje natural en SQL, esta es la superficie que importa, y está probada
contra la base real.

**El instalador no se queda atrás del código.** `instalador-al-dia.test.js`
compara fechas de commit: falla si algún archivo de `app-python/` es más nuevo
que el `.exe` publicado. Es el tipo de test que evita vender una descarga
vieja.

## Un detalle del test de instalador (no es un defecto)

Ese test **falla en un clon shallow** y lo dice con el remedio exacto:
"el repo está clonado en modo shallow… poné `fetch-depth: 0`". Lo verifiqué:
con `--depth 1` da rojo; con la historia traída, verde. El CI del repo ya usa
`actions/checkout@v7` con `fetch-depth: 0` y el comentario explicando por qué,
así que **no hay nada que arreglar** — queda anotado para que la próxima vez
que alguien lo vea rojo en su máquina sepa que es el clon, no el producto.

## Por qué 9 y no 10

Ningún tope duro aplica. Lo que falta:

1. **Sin E2E de navegador.** La suite cubre motor y web por unidad; nada
   recorre la pantalla que ve el usuario final.
2. **Sin humo post-deploy.** Nada verifica que la URL publicada responda.
3. **Sin cobro real verificado**, si el producto se vende con licencia.

## Próxima acción

Antes de cada push: `npm test && npm run lint` — con la historia de git
completa, o `instalador-al-dia.test.js` da un rojo que no es real.
