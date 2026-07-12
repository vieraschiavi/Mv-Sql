# 📊 Plan de negocio — MV SQL NLP

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
- **Prueba 3 días full** = 30 créditos de cortesía (costo para nosotros < US$ 0,50 por trial).

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
tiempo — cobrar la implementación lo convierte en ingreso; (c) el trial de 3
días con créditos nuestros puede abusarse — limitar por email verificado + device.

## 6. Checklist de lanzamiento (orden sugerido)

- [ ] Deploy de `web/` en Vercel + dominio (ej. mvsqlnlp.com)
- [ ] Grabar el video demo (guion en `GUION_VIDEO_DEMO.md`) y embeberlo
- [ ] Compilar el instalador Windows (`desktop/`, `npm run dist`) y firmarlo
- [ ] Alta MercadoPago + endpoints de pago (ver `INTEGRACION_MERCADOPAGO.md`)
- [ ] Sistema de licencias (JWT firmado) + trial 3 días
- [ ] Monotributo + facturación electrónica
- [ ] 5 clientes beta (gratis 1 mes a cambio de testimonio)
- [ ] Lanzamiento: YouTube + LinkedIn + US$ 300 ads
