# 📊 Plan de negocio — MV SQL NLP

> ⚠️ **CORRECCIÓN (auditoría jul-2026).** Este documento recomienda suscripción
> (US$ 15/29/79 por mes) pero el código publicado cobra **pago único**
> (US$ 19/39/99) — son dos negocios distintos y el implementado es el peor.
> A US$ 39 de pago único hacen falta **106 ventas por mes, para siempre**,
> contra un mercado uruguayo alcanzable de ~684 empresas: es imposible.
> El mismo ingreso se logra con **1,7 implementaciones por mes** a US$ 2.500.
>
> **Conclusión de la auditoría: el producto es el diferenciador, el servicio de
> implementación es el negocio.** Modelo completo y editable en
> [`MODELO_NEGOCIO.py`](MODELO_NEGOCIO.py) — corrélo con `python3 MODELO_NEGOCIO.py`
> antes de tomar decisiones con plata.
>
> Escenarios a 18 meses (neto acumulado): pago único **-US$ 14.298** ·
> suscripción + servicio **+US$ 114.913** · con publicidad y equipo **+US$ 207.102**.

> Análisis de competencia, precios recomendados, estructura de costos y
> escenarios de facturación neta. Cifras en USD salvo indicación. Los valores
> de mercado son estimaciones a verificar antes de lanzar (los precios de
> competidores y comisiones cambian seguido).

---

## 1. Competencia (text-to-SQL / NL2SQL)

| Competidor | Qué hace | Precio (aprox.) | Debilidad que MV SQL NLP explota |
|---|---|---|---|
| **AI2sql** | Generador NL→SQL web | ~US$ 6–33/mes | No ejecuta contra tu base: solo genera texto SQL. Sin validación de esquema real. |
| **Text2SQL.ai** | Generador NL→SQL + explicador | ~US$ 4–10/mes | Igual: no se conecta a la base, sin gráficos ni exportes. |
| **SQLAI.ai** | Suite de generación/optimización SQL | ~US$ 7–30/mes | Conexión limitada, interfaz solo en inglés. |
| **Vanna.ai** | Framework Python RAG text-to-SQL (open source + cloud) | Gratis / planes cloud | Requiere saber programar — no es producto final para usuario de negocio. |
| **Chat2DB** | Cliente de BD con copiloto IA | Gratis / ~US$ 10–20/mes Pro | Es un IDE para gente técnica, no para gerentes; español pobre. |
| **AskYourDatabase** | Chat con tu BD (desktop/web) | ~US$ 19–39/mes | Sin intervalo de confianza, sin multi-proveedor de IA, sin créditos locales. |
| **Outerbase / Basedash** | UI de datos con IA para equipos | ~US$ 20–50/usuario/mes | Cloud-first: hay que subir/conectar la base a su nube — rechazo en pymes con datos sensibles. |
| **Seek AI / Wren AI** | Enterprise NL analytics | Cotización (miles US$/año) | Fuera del alcance de pymes LATAM. |
| **DBeaver AI / copilotos de IDE** | Asistente dentro del IDE SQL | Incluido en licencia | Para desarrolladores; no exporta reportes ni explica en negocio. |

**Huecos de mercado claros (nuestros diferenciales):**
1. **Español/portugués nativo + voseo + soporte LATAM** — casi toda la competencia es inglés-primero.
2. **Ejecución local con datos que no salen de la red** — clave para financieras, salud, estudios contables.
3. **IA a elección + modo créditos facturado por nosotros** — nadie ofrece "traé tu key o comprá créditos" con MercadoPago.
4. **Intervalo de confianza** — ningún competidor directo lo muestra; es un argumento de venta fuerte ("sabés cuándo confiar").
5. **App de escritorio instalable** — la mayoría es SaaS web; en LATAM pyme el software instalado "de una vez" sigue vendiendo.

## 2. Precio recomendado

Posicionarse **apenas por encima del generador barato (US$ 10) y muy por debajo
del enterprise (US$ 50+)**, porque entregamos más que los baratos (ejecución,
gráficos, confianza, exportes) con costo de venta LATAM.

**Suscripción (el cliente pone su API key → nuestro costo de IA = $0):**
- Personal **US$ 15/mes** · Profesional **US$ 29/mes** (ancla, "más popular") · Empresa **US$ 79/mes** (5 puestos)
- En Argentina publicar precio en pesos actualizado mensualmente (MP cobra en ARS).
- Anual con 2 meses gratis (mejora caja y retención).

**Créditos (nosotros ponemos la IA y la facturamos):**
- 100 créditos **US$ 9** · 500 **US$ 35** · 2000 **US$ 110**
- Costo real de IA por consulta (con modelos económicos tipo Haiku / GPT-4o-mini /
  Gemini Flash, ~3–4k tokens in + ~400 out, incluyendo reintento y explicación):
  **≈ US$ 0,004–0,015**. Margen bruto del crédito: **85–95%**. Es el producto más
  rentable y el más fácil de vender ("no necesitás saber qué es una API key").
- **Prueba 7 días full** = 30 créditos de cortesía (costo para nosotros < US$ 0,50 por trial).

## 3. Estructura de costos

### Costos fijos mensuales (escenario Argentina, arranque solo)

| Concepto | US$/mes (aprox.) |
|---|---|
| Monotributo (categoría media, hasta que factures ~US$ 2.500/mes) | 40–80 |
| Vercel (hobby→Pro cuando haya tráfico) | 0–20 |
| Dominio + email transaccional | 5 |
| Certificado de firma de código (para el .exe, ~US$ 100–400/año) | 10–35 |
| Contador | 30–60 |
| **Total base** | **~85–200** |

- **SAS** (si escala o entran socios): constitución ~US$ 300–600 una vez +
  contador ~US$ 100–200/mes + Ingresos Brutos/IVA según jurisdicción. Recién
  conviene al superar los topes de monotributo o al facturar al exterior en escala.
- **Uruguay** (alternativa para cobrar global): empresa unipersonal/SAS UY,
  costos fijos mayores (~US$ 150–350/mes) pero mejor acceso a divisas.
- **MercadoPago**: comisión ~**6–8% + IVA** según plazo de acreditación y país.
  Ya contemplado en los márgenes de abajo (uso 8% total).

### Publicidad

- Google Ads en LATAM para keywords B2B de datos: **CPC ≈ US$ 0,3–1,5**.
- Presupuesto mínimo útil: **US$ 150–300/mes**. Con landing buena y video,
  una conversión visita→trial de 3–6% y trial→pago de 15–25% es alcanzable.
- Canales gratis que en este nicho rinden más que los ads al principio:
  YouTube (el video demo + tutoriales "consultá tu SQL Server sin saber SQL"),
  LinkedIn, grupos de contadores/consultores, TikTok técnico.

### Unidad económica de los créditos de IA (¿riesgo de margen negativo?)

La objeción razonable: "si vendés créditos de IA a precio fijo y el consumo
es variable, podés quedar en margen negativo". La respuesta está en el
diseño, no en una promesa — todo lo de abajo es verificable en el código:

- **1 crédito = 1 llamada a la IA** (`web/api/ai-proxy.js`: `kv.incr` por
  request). Una pregunta con análisis activado consume 2 créditos (SQL +
  análisis); con el modo privacidad estricta, 1.
- **El costo por llamada está acotado por diseño**: el modelo es fijo
  (Claude Haiku 4.5), la salida está topeada (`max_tokens ≤ 1500`) y la
  entrada también, porque el RAG manda solo las ~4 tablas relevantes
  (`motor.py`, `k=4`) — nunca el catálogo entero, por grande que sea la base.
- **Números** (precios API Haiku 4.5: US$ 1/M tokens entrada, US$ 5/M salida):

  | Pack | Precio | ¢/crédito | Costo típico/crédito¹ | Margen bruto |
  |---|---|---|---|---|
  | 100 créditos | US$ 9 | 9,0¢ | ~1,3–1,8¢ | ~80–86% |
  | 500 créditos | US$ 35 | 7,0¢ | ~1,3–1,8¢ | ~74–81% |
  | 2000 créditos | US$ 110 | 5,5¢ | ~1,3–1,8¢ | ~67–76% |

  ¹ Entrada ~5–10k tokens (esquema de 4 tablas + pregunta) + salida tope
  1500. Peor caso extremo (esquemas gigantes por tabla): ~6¢/crédito —
  todavía margen positivo en todos los packs. Restaría la comisión de
  MercadoPago (~8%) sobre el precio del pack.
- **Sin cola infinita**: si el contador de créditos (Vercel KV) no está
  disponible, el proxy **rechaza el pedido en vez de servir IA sin tope**
  (fail-closed, testeado en `web/tests/suscripcion.test.js`). El crédito se
  descuenta *antes* de llamar a la IA: pedidos en paralelo no pueden
  consumir de más.
- El pack es **pago único, no suscripción**: agotados los créditos, el
  cliente compra otro pack o pasa a su propia API key. No existe el caso
  "cliente que consume para siempre a costo nuestro".

### Precisión y responsabilidad (la otra objeción de compra)

- Lo que el producto **garantiza por construcción**: el SQL se valida contra
  el esquema real antes de ejecutarse (lo inexistente se rechaza y se
  autocorrige), la conexión es de solo lectura al nivel del conector (test
  público de inyección directa en `app-python/tests/test_solo_lectura.py`),
  y el SQL ejecutado siempre queda visible para auditarlo.
- Lo que **no se promete**: una tasa de acierto medida. El % de confianza
  que muestra cada respuesta (autoevaluación del modelo + señal RAG +
  validación estructural) es una guía de cuándo revisar, no una métrica
  auditada — decirlo así en la venta evita la sobre-promesa que después
  cuesta el contrato. El peor caso posible es un número incorrecto en
  pantalla; nunca un dato modificado.
- Responsabilidad: el EULA (punto 4, en los 3 idiomas) establece que el
  software se provee "tal cual" y que el usuario debe revisar las consultas
  antes de decidir con ellas. La aceptación del EULA es obligatoria y
  queda registrada (`app-python/eula.py`).

## 4. Escenarios de facturación neta (12 meses)

Supuestos: mezcla 60% suscripción (ticket promedio US$ 25) + 40% créditos
(recompra promedio US$ 20/mes por cliente activo), MP 8%, IA de créditos 8%
del ingreso de créditos, churn mensual 6%, publicidad según escenario.

| | **Conservador** | **Base** | **Optimista** |
|---|---|---|---|
| Clientes pagos al mes 12 | 30 | 120 | 400 |
| MRR bruto (mes 12) | US$ 700 | US$ 2.800 | US$ 9.500 |
| Ingresos año 1 (acumulado) | US$ 4.200 | US$ 17.000 | US$ 57.000 |
| Publicidad año 1 | US$ 1.200 | US$ 3.600 | US$ 9.000 |
| Costos fijos + comisiones año 1 | US$ 1.800 | US$ 3.400 | US$ 9.500 |
| **Neto año 1** | **≈ US$ 1.200** | **≈ US$ 10.000** | **≈ US$ 38.500** |
| Horas/semana requeridas | 5–8 | 10–15 | 25+ (soporte/ventas) |

Claves del escenario base: 10 clientes nuevos/mes desde el mes 4, sostenidos
por el video demo + contenido + US$ 300/mes de ads. Es un negocio de
**acumulación lenta**: el año 2 con el mismo ritmo duplica o triplica el MRR
porque el churn se compensa con base instalada.

## 5. ¿Uso propio o venderlo?

**Recomendación: ambos, en este orden.**

1. **Usalo ya para vos / tu trabajo** (costo cero: Ollama local o tu propia key).
   Cada consulta real que hagas es QA gratis y material de demo.
2. **Vendelo como servicio con implementación, no solo como licencia.** El plan
   Empresa con "instalación asistida + capacitación" permite cobrar además
   **US$ 150–400 por implementación** (conectar su base, armar 10 consultas
   guardadas de su negocio). En LATAM pyme, ese acompañamiento ES el producto.
   3 implementaciones/mes ya superan el escenario conservador completo.
3. **Recién después** invertí fuerte en ads/SEO para el plan autoservicio.

**Por qué no "solo uso propio":** el costo marginal de venderlo es bajísimo
(la web ya está, el instalador ya está) y el mercado hispano de NL2SQL está
casi vacío. **Por qué no "solo venderlo":** sin casos de uso propios reales,
el producto se estanca — los competidores globales iteran rápido.

**Riesgos honestos:** (a) los grandes (Microsoft Copilot, etc.) integran
NL2SQL gratis en sus stacks — el diferencial defendible es LATAM + on-premise +
acompañamiento; (b) soporte técnico de conexiones a bases ajenas consume
tiempo — cobrar la implementación lo convierte en ingreso; (c) el trial de 7
días con créditos nuestros puede abusarse — limitar por email verificado + device.

## 6. Checklist de lanzamiento (orden sugerido)

- [ ] Deploy de `web/` en Vercel + dominio (ej. mvsqlnlp.com)
- [ ] Grabar el video demo (guion en `GUION_VIDEO_DEMO.md`) y embeberlo
- [ ] Compilar el instalador Windows (`desktop/`, `npm run dist`) y firmarlo
- [ ] Alta MercadoPago + endpoints de pago (ver `INTEGRACION_MERCADOPAGO.md`)
- [x] Sistema de licencias (JWT firmado) + trial 7 días — trial ahora se hace
  cumplir de verdad en `app-python/licencia.py` (antes solo era texto de la
  web, la app corría sin límite); las descargas pagas (own_ai y credits)
  quedan eximidas vía `licencia_mvsql.json`
- [ ] Monotributo + facturación electrónica
- [ ] 5 clientes beta (gratis 1 mes a cambio de testimonio)
- [ ] Lanzamiento: YouTube + LinkedIn + US$ 300 ads

## 7. Estado actual, sin maquillar (para quien evalúe el negocio)

Quien mire este proyecto con ojos de comprador o inversor va a preguntar
esto; mejor que la respuesta esté escrita y sea verificable:

| Pregunta | Respuesta honesta hoy |
|---|---|
| ¿Clientes actuales? | Ninguno público todavía. Las reseñas de la landing arrancan vacías **a propósito** (`web/assets/resenas.json` = `[]`): cero contenido inventado. El primer objetivo comercial son los 5 beta del checklist. |
| ¿Tracción? | Producto completo y testeado (suite pública en CI), web de pago funcionando (MercadoPago), instalador Windows. Ingresos: aún no. |
| ¿Equipo? | Fundador único (Martín Viera). El riesgo de bus factor es real; lo compensa parcialmente que el código, los tests y este plan están documentados para transferirse. |
| ¿Financiamiento? | Autofinanciado. Sin deuda ni inversores; los costos fijos de arranque son ~US$ 85–200/mes (sección 3). |
| ¿Canal de venta? | Directo: demo en video + trial de 7 días autoservicio en la web, e implementación como servicio (el material de venta en 3 idiomas está en `docs/VENTA_*`). Sin partners todavía. |
| ¿"Siete países"? | La cobertura idiomática (ES/EN/PT) y el cobro vía MercadoPago habilitan LATAM; no hay operación ni clientes en múltiples países hoy. Es mercado direccionable, no presencia — no venderlo como lo segundo. |
| ¿Margen de los créditos? | Acotado por diseño, no por promesa (sección 3, unidad económica): 1 crédito = 1 llamada, entrada y salida topeadas, proxy fail-closed. |
| ¿Certificaciones? | Ninguna todavía (ISO/SOC2 no aplican al tamaño actual). La arquitectura local minimiza qué habría que certificar: los datos del cliente nunca pasan por servidores propios, salvo el tránsito de la consulta en modo créditos, que no se almacena. |
