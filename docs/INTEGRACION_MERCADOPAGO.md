# 💳 Compra y descarga por MercadoPago — MV SQL NLP

Implementado y funcionando en el repo (`web/api/*.js`): el cliente paga un
**pago único** con MercadoPago Checkout Pro y descarga el producto al toque,
sin backend propio ni base de datos — todo corre como Vercel Serverless
Functions + licencias firmadas (JWT), igual de simple que descargar el zip
de ejemplo original pero gateado por el pago.

## Modelo de cobro

| Producto | Precio (pago único) | Qué recibe el cliente |
|---|---|---|
| Personal / Profesional / Empresa — **IA propia** | US$ 19 / 39 / 99 | El zip de la app. Configura su propia API key de Claude/GPT/Gemini/etc. |
| Personal / Profesional / Empresa — **créditos embebidos** | US$ 9 / 35 / 110 | El **mismo zip**, pero con `nl2sql_rag/licencia_mvsql.json` ya cargado: elige el proveedor **"MV SQL Créditos"** en la app y pregunta sin configurar nada — la IA la pagamos nosotros y se factura en el precio. |
| Suscripciones recurrentes (sección "Precios") | US$ 15/29/79 por mes | Se mantienen para el modelo SaaS de acceso continuo; usan el mismo Checkout Pro con `preapproval` si se decide activarlas (no implementado en esta iteración — ver nota al final). |

Comisión de MercadoPago (Argentina, acreditación estándar): ≈6–8 % + IVA por
transacción — ya contemplada en el margen de `docs/PLAN_DE_NEGOCIO.md`.

## Cómo funciona (flujo real, sin base de datos)

```
Cliente en mvsqlnlp.com/#download
  → elige modo (IA propia / créditos) + plan + email
  → POST /api/create-preference          (crea el Checkout Pro)
  → redirige a MercadoPago, paga
  → MercadoPago lo devuelve a /gracias?payment_id=...
  → /gracias llama GET /api/verify-and-issue?payment_id=...
       · re-verifica el pago EN VIVO contra la API de MercadoPago
         (nunca confía en el query string)
       · si está aprobado, firma un JWT de licencia (JWT, sin DB)
  → /gracias muestra el botón "Descargar" → GET /api/download?token=...
       · modo "own_ai":  sirve downloads/mvsql-nlp-app.zip tal cual
       · modo "credits": inyecta licencia_mvsql.json dentro del zip al vuelo
         (con JSZip) antes de devolverlo — nunca se genera ni guarda en disco
```

No hace falta base de datos porque el JWT firmado ES la licencia: contiene
`email`, `plan`, `mode`, `credits` y expira a los 365 días. `verify-and-issue`
solo se ejecuta cuando MercadoPago confirma el pago, así que no hay estado
que sincronizar.

### Archivos

```
web/api/_mp.js              cliente de MercadoPago (Preference/Payment)
web/api/_license.js         emitir/verificar JWT de licencia
web/api/_products.js        catálogo de precios (plan+modo → título/precio)
web/api/create-preference.js  POST → crea el link de pago
web/api/verify-and-issue.js   GET  → re-verifica el pago y emite el token
web/api/webhook.js          POST → notificación IPN de MP (solo logging)
web/api/download.js         GET  → sirve el zip, gateado por token
web/api/ai-proxy.js         POST → IA server-side para el modo "créditos"
web/downloads/mvsql-nlp-app.zip   paquete descargable (app-python empaquetada)
web/gracias/index.html      página de éxito: verifica pago y ofrece descarga
web/pago-fallido/index.html   página de pago no completado
web/assets/purchase.js      lógica de compra en la landing (#download)
```

## Variables de entorno requeridas en Vercel

| Variable | Para qué |
|---|---|
| `MP_ACCESS_TOKEN` | Credencial de producción de MercadoPago (Developers → Credenciales) |
| `LICENSE_SECRET` | String random largo — firma los JWT de licencia. **Nunca lo cambies** una vez emitidas licencias, o todas se invalidan |
| `ANTHROPIC_API_KEY` | Solo si vendés el modo "créditos embebidos": es la key que factura por vos las consultas de esos clientes |

Opcional (recomendado antes de vender créditos en volumen):

| Variable | Para qué |
|---|---|
| `KV_REST_API_URL` / `KV_REST_API_TOKEN` | Conectar **Vercel KV** (Storage → KV en el dashboard) para descontar créditos de verdad por licencia. Sin esto, `ai-proxy.js` funciona pero **no aplica el tope de créditos** server-side (lo documenta en el propio código) — aceptable para las primeras ventas, no para escalar. |

## Cómo activarlo (checklist)

1. Cuenta de MercadoPago verificada (vendedor) → sacar `MP_ACCESS_TOKEN` de producción.
2. En Vercel: Project Settings → Environment Variables → cargar `MP_ACCESS_TOKEN`, `LICENSE_SECRET` (generar con `openssl rand -hex 32`), y `ANTHROPIC_API_KEY`.
3. Deploy (`vercel --prod` o conectar el repo por Git — ver README del repo).
4. Probar el flujo completo con una compra real de bajo monto antes de anunciar.
5. (Opcional) Agregar Vercel KV para metering real de créditos.
6. (Opcional) Reemplazar el zip base por builds más recientes: pisar `web/downloads/mvsql-nlp-app.zip` con el contenido actualizado de `app-python/` antes de cada release.

## Nota sobre las suscripciones recurrentes

La sección "Precios" de la landing mantiene los 3 planes mensuales (SaaS
tradicional) como opción para quien prefiera pago continuo con soporte y
actualizaciones — para activarlos de verdad hace falta un endpoint adicional
con `preapproval` (suscripción) en vez de `preference` (pago único), y sí
requiere donde guardar el estado de la suscripción (Vercel KV o una base
real). Lo dejamos documentado para una segunda iteración; el flujo de
**pago único → descarga** de esta sección ya está completo y funcional.
