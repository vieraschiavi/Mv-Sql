# 🎯 Guion de demo — 20 minutos

Para la reunión con un gerente de datos, cobranzas o administración. No es una
demo de producto: es una demo de **su** problema.

**Regla de oro:** si en el minuto 5 no estás mostrando **su** base de datos, la
reunión ya se perdió. La demo con `cartera_demo.db` es el plan B, no el A.

---

## Antes de la reunión (30 minutos de preparación)

Pedile por mail, dos días antes:

> "Para que la demo sea sobre tus datos y no sobre un ejemplo genérico,
> necesito solo dos cosas: un usuario de **solo lectura** a la base (o a una
> copia), y las 3 preguntas que más te piden y hoy te cuesta responder.
> Con eso llego con todo andando."

Si te dan acceso: conectá, mirá el esquema y **preparate 2 respuestas correctas
de antemano**. Nunca improvises la primera consulta delante del cliente.

Si no te dan acceso (lo más común la primera vez): pedí igual **las 3 preguntas**
y un Excel exportado de su sistema. Con el modo Archivo tenés demo real igual.

---

## Minuto a minuto

### 0–2 · El problema, con sus palabras
No abras el programa todavía.

> "Antes de mostrarte nada: cuando vos pedís un número que no está en un
> reporte fijo, ¿cómo lo conseguís hoy? ¿A quién se lo pedís y cuánto tarda?"

Dejalo hablar. Anotá el número que diga (tres días, una semana, "depende").
**Ese número es tu precio justificado el resto de la reunión.**

### 2–5 · La pregunta de él, respondida en vivo
Abrí el programa ya conectado a su base. Escribí **la pregunta que él te mandó
por mail**, textual.

Mientras genera, narrá lo que pasa:

> "Fijate que no le mandé tus datos a ninguna IA: solo le describí los nombres
> de tus tablas. Las filas nunca salen de tu red."

Mostrá el resultado. Callate y dejá que lo mire.

### 5–8 · Por qué puede confiar
Acá se gana o se pierde la venta. El miedo real del comprador es
*"¿y si el número está mal y yo lo llevo a una reunión?"*.

1. **El SQL a la vista** — "Podés dárselo a tu equipo técnico para que lo revise."
2. **La validación** — "Si la IA inventa una columna que no existe, se rechaza y
   se corrige sola. No te devuelve un número inventado."
3. **El intervalo de confianza** — "Cuando no está segura, te lo dice. Eso no lo
   hace ChatGPT."

> "¿Cómo verificarías vos que este número está bien?" — y hacelo con él en el momento.

### 8–12 · La segunda pregunta (la que no se anima a pedir)
> "Ahora hacé vos la pregunta. La que normalmente no pedirías porque no vale la
> pena molestar a Sistemas."

**Este es el momento que vende.** Cuando ve que puede preguntar cualquier cosa
sin costo, cambia la cara. Si sale mal, mejor: mostrá cómo se corrige y cómo la
consulta se guarda para que salga bien siempre.

### 12–16 · Lo que ChatGPT no puede darle
Mostrá **Equipo y permisos** y **Auditoría**:

> "Esto lo podés dar a tu equipo sin miedo. Cada persona ve solo sus tablas —
> el de cobranzas no ve sueldos. Y todo lo que cada uno consulta queda
> registrado acá, con fecha y usuario, exportable para auditoría."

Si es una financiera, un estudio contable o algo regulado, **esto solo justifica
el precio**. Es lo único que no puede replicar con una suscripción a ChatGPT.

### 16–20 · El cierre
No preguntes "¿qué te pareció?". Preguntá:

> "¿Qué tendría que pasar para que esto esté andando en tu equipo el mes que viene?"

Escuchá la objeción real (presupuesto, IT, "lo tengo que hablar con…"), y cerrá
con el paso concreto:

> "Te mando hoy la propuesta con alcance cerrado y precio fijo. Si te sirve, la
> implementación lleva 2 semanas y arrancamos cuando digas."

---

## Objeciones frecuentes y qué responder

| Dice | Qué está pensando | Respuesta |
|---|---|---|
| "Esto lo hago con ChatGPT" | No ve el diferencial | "Probá: subile un Excel y pedile el cobrado por sucursal. Ahora hacelo con 40 millones de filas, sin sacar los datos de tu red, y que quede registrado quién lo consultó. Ahí está la diferencia." |
| "¿Y si la IA se equivoca?" | Miedo a quedar mal | "Se equivoca, sí. Por eso el SQL está a la vista y validado contra tu esquema, y por eso cada respuesta trae su intervalo de confianza. No te pido que confíes: te pido que verifiques." |
| "Tengo que hablarlo con Sistemas" | Necesita aliado interno | "Perfecto, sumalo a la próxima. A Sistemas le sacás trabajo de encima: dejan de ser la cola de pedidos. Y la conexión es de solo lectura, lo van a agradecer." |
| "Es caro" | No ató el precio al costo actual | "¿Cuántas horas por mes gasta tu equipo armando reportes a mano? A [su número] horas, esto se paga en [X] meses. Y después es ganancia todos los meses." |
| "Mandame info y lo veo" | No le movió la aguja | "Te la mando. ¿Puedo hacerte una última pregunta? ¿Qué te hubiera tenido que mostrar hoy para que esto fuera prioridad?" — la respuesta vale más que la venta. |

---

## Después de la reunión (mismo día, no al otro)

Mail corto:

> Asunto: **La consulta que vimos hoy + propuesta**
>
> [Nombre], te dejo el SQL de la consulta que corrimos, para que tu equipo lo
> revise cuando quiera. Adjunto la propuesta con el alcance cerrado y el precio
> fijo que hablamos.
>
> Quedo a la orden.

Adjuntá el SQL real que generaron juntos. **Es la prueba de que la reunión fue
sobre su negocio y no sobre un producto.**
