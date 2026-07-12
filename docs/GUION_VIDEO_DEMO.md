# 🎬 Guion del video demostrativo — MV SQL NLP

> ✅ **Ya publicado:** `web/assets/video/demo.webm` — captura de pantalla real
> (27s) de la landing con la demo animada, embebida en la sección "Miralo en
> acción" de la web. Es una captura del sitio, **sin narración de voz**: no
> hay herramienta de síntesis de voz conectada en este entorno para generar
> el audio rioplatense. Lo que falta para la versión final de 2 minutos con
> voz — grabar la app real (no solo la landing) y sumar la narración — está
> detallado abajo, listo para producir con OBS + ElevenLabs/Azure TTS.

**Duración objetivo:** 2:00–2:30 min
**Voz:** rioplatense (español de Argentina/Uruguay), tono cercano y profesional. Voseo natural ("mirá", "tenés", "preguntale").
**Ritmo:** sin pausas muertas — cada frase acompaña una acción en pantalla. Grabar la pantalla a 60 fps para que se vea fluido, sin lag.

## Cómo producirlo (recomendado)

| Elemento | Herramienta | Nota |
|---|---|---|
| Voz en off rioplatense | ElevenLabs (voz clonada propia o voz "es-AR"), o Azure TTS `es-AR-TomasNeural` / `es-UY-MateoNeural` | Exportar WAV 48 kHz |
| Captura de pantalla | OBS Studio (60 fps, 1080p) | Grabar la app de escritorio con la base demo |
| Edición | CapCut / DaVinci Resolve (gratis) | Cortes al ritmo del guion, zooms suaves |
| Música | Fondo tech suave a -20 dB | Sin copyright |
| Subtítulos | ES + EN + PT quemados o como .srt | La web es trilingüe: subir 3 versiones o 1 con subtítulos |

Publicar en YouTube (unlisted) y embeber en la sección "Demo" de la web:
reemplazar el placeholder de `web/index.html` (sección `#video`) por el `<video>` o iframe.

---

## Guion (voz en off + acción en pantalla)

**[0:00–0:10] — Gancho**
> 🎙 "¿Cuántas veces necesitaste un dato de tu sistema… y terminaste esperando días a que alguien te arme el reporte? Mirá esto."

*Pantalla: escritorio de Windows, doble clic en el ícono de MV SQL NLP. La app abre al instante.*

**[0:10–0:25] — Conexión**
> 🎙 "Esto es MV SQL NLP. Se conecta a la base de datos que ya tenés: SQL Server, MySQL, PostgreSQL o SQLite. Elegís el motor, ponés tus credenciales, y listo: lee tu esquema completo en segundos. Solo lectura, así que tus datos están seguros."

*Pantalla: panel izquierdo → elegir "SQL Server" → conectar → aparece "✓ 6 tablas cargadas" y se despliega el esquema.*

**[0:25–0:40] — La IA que vos elijas**
> 🎙 "¿La inteligencia artificial? La elegís vos. Claude, GPT, Gemini, Groq… o tu propio servidor local con Ollama, gratis. Ponés tu API key o usás nuestros créditos, y nosotros te facturamos todo junto."

*Pantalla: abrir el menú de proveedores de IA, mostrar la lista completa, elegir uno, clic en "Probar conexión" → "✓ Conexión OK".*

**[0:40–1:10] — La magia (consulta principal)**
> 🎙 "Y ahora sí: preguntale a tu base como le preguntarías a una persona. 'Cuánto facturamos por mes este año, por sucursal'. Enter. Mirá lo que hace: detecta las tablas correctas, genera un SQL profesional —optimizado con CTEs, como lo escribiría un experto— lo valida contra tu esquema real para no inventarse nada… y te muestra el resultado con su intervalo de confianza: noventa y dos por ciento. Sabés exactamente cuánto confiar en cada respuesta."

*Pantalla: tipear la pregunta, Enter. Mostrar en secuencia: chips de tablas detectadas → SQL con WITH…AS resaltado → check verde de validación → barra de confianza 92% (±5). Zoom suave en cada elemento.*

**[1:10–1:30] — Resultados: tabla, gráfico, análisis**
> 🎙 "Tabla al instante. Gráfico automático. Y un análisis en tu idioma: 'la facturación crece un ocho por ciento mensual y la sucursal Centro lidera con el treinta y ocho por ciento del total'. Todo exportable a Excel, CSV, PDF o HTML con un clic."

*Pantalla: pasar por las pestañas Tabla → Gráfico (barras animadas) → Análisis. Clic en "⬇ Excel", se abre el archivo exportado con formato.*

**[1:30–1:50] — Guardar, procedures, optimizar**
> 🎙 "¿Te gustó la consulta? Guardala con un nombre y reutilizala cuando quieras. ¿Necesitás dejarla instalada en el servidor? Un clic y te la convierte en stored procedure listo para producción. Y si ya tenés SQL viejo y lento, pegalo: te lo reescribe optimizado."

*Pantalla: guardar como "Facturación mensual por sucursal" → aparece en el panel de guardadas → clic en "Stored procedure" → se muestra el código generado.*

**[1:50–2:10] — Cierre + oferta**
> 🎙 "MV SQL NLP. Tu base de datos, en tu idioma: español, inglés o portugués. Probalo gratis tres días, con todas las funciones, sin tarjeta. Y cuando te convenza, pagás como quieras: suscripción con tu propia API, o créditos que te facturamos nosotros — con MercadoPago, en tu moneda."

*Pantalla: corte a la web (landing), scroll por precios, badge de MercadoPago, botón "Probar gratis 3 días". Logo final ⚡ MV SQL NLP + URL.*

**[2:10] — Placa final**
> Texto en pantalla: **MV SQL NLP — Dejá de esperar reportes. Preguntale a tu base.** + URL + "Prueba gratis 3 días".

---

## Checklist de calidad ("sin lag")

- [ ] Grabar en una máquina con la base demo ya cargada (respuestas < 2 s).
- [ ] Si la IA tarda, cortar la espera en edición — el video nunca muestra spinners de más de 1 s.
- [ ] 60 fps, cursor suavizado, zooms de 110–120% en los momentos clave.
- [ ] Audio: -14 LUFS, sin ruido de fondo, voz por encima de la música.
- [ ] Exportar 1080p H.264 (o 4K si YouTube). Peso final < 100 MB para carga rápida.
