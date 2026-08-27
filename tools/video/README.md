# 🎬 Video de demo — cómo se regenera

Los tres videos de la landing (`web/assets/video/demo_es.mp4`, `demo_en.mp4`,
`demo_pt.mp4`) no se editan a mano: se generan desde acá. Si cambia la app o
cambia el mensaje comercial, se corre esto y quedan los tres al día.

**El poster sale del mismo comando.** `armar.py` guarda además
`web/assets/video/poster_<idioma>.png`, que es el primer cuadro del video
que acaba de armar. Antes había un único `video-poster.png` para los tres
idiomas — y era la og-image horizontal metida en un marco vertical, así que
el texto salía cortado a mitad de palabra. Generarlo acá hace imposible que
se vuelva a descuadrar o a quedar en otro idioma que el del video.

**Sobre el proxy:** `edge-tts` habla por WebSocket y falla la verificación
TLS detrás del proxy del entorno. `armar.py` ya lo resuelve agregando la CA
de `/root/.ccr/ca-bundle.crt` al bundle de `certifi` al importarse, así que
no hace falta salida directa a internet. Si el servicio de voz devuelve
`NoAudioReceived`, es transitorio: reintentar el idioma que falló.

**Los tres videos son distintos de verdad:** la interfaz de la app se graba en
cada idioma, no solo la narración. Un prospecto brasileño no ve una pantalla en
castellano.

## Qué hay acá

| Archivo | Para qué |
|---|---|
| `guion.py` | El texto: narración, rótulos y voz de cada idioma. **Es el único archivo que hay que tocar para cambiar el mensaje.** |
| `sembrar_demo.py` | Crea el equipo, la auditoría y la licencia de créditos que se ven en cámara |
| `app_demo.py` | La app real con la IA simulada (para no depender de una API key ni de que el modelo conteste distinto cada vez) |
| `capturar.mjs` | Maneja la app con el navegador y saca una captura por bloque, en el idioma que se pida |
| `armar.py` | Arma el video: narración con edge-tts, cuadros con PIL y montaje con ffmpeg |

## Cómo se corre

```bash
# 1. escenografía (equipo, auditoría, licencia — todo gitignoreado)
python tools/video/sembrar_demo.py

# 2. levantar la app con la IA simulada
streamlit run tools/video/app_demo.py --server.port 8899 \
  --server.headless true --theme.base dark

# 3. capturar y armar, un idioma por vez
for L in es en pt; do
  node tools/video/capturar.mjs $L /tmp/cap_$L
  python tools/video/armar.py $L /tmp/cap_$L web/assets/video/demo_$L.mp4
done
```

Necesita `playwright` (está en `web/node_modules` o instalado global),
`edge-tts`, `Pillow`, `numpy` e `imageio-ffmpeg`.

## Decisiones que conviene no deshacer

- **Vertical 1080×1920.** Mismo formato que el video de MV Kobra: sirve igual
  embebido en la web que mandado por WhatsApp o subido a Instagram y LinkedIn,
  que es donde se comparte.
- **Una sola marca por cuadro.** Las capturas se desplazan para dejar el
  encabezado de la app fuera de plano; si no, "MV SQL NLP" aparecería dos veces
  en el mismo frame.
- **Cada bloque dura lo que dura su narración.** Por eso el video en portugués
  dura más que el de castellano. Forzarlos a durar igual obliga a meter
  silencios o a cortar frases.
- **Texto y captura nunca comparten franja.** El titular arriba, la ventana en
  el medio, el rótulo abajo: es imposible que se pisen.
- **Los bordes de la captura se desvanecen.** Una captura siempre corta una
  fila de texto por la mitad; con el degradado se lee como intencional.
- **El panel Explorar se graba sobre una tabla entera**, no sobre el resultado
  de dos columnas: una matriz de correlación de 2×2 toda roja no muestra nada.
