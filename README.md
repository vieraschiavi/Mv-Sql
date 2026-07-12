# ⚡ MV SQL NLP

**Tu base de datos, en tu idioma.** Consultá cualquier base SQL en lenguaje
natural (español, inglés o portugués), sin saber una línea de código. La IA
genera SQL profesional optimizado con CTEs, lo valida contra tu esquema real,
te muestra el **intervalo de confianza** de cada respuesta y devuelve tablas,
gráficos y análisis exportables a Excel, CSV, PDF y HTML.

## 📦 Qué hay en este repositorio

| Carpeta | Qué es |
|---|---|
| [`web/`](web/) | Landing comercial (estilo SaaS dark) lista para **Vercel** — 3 idiomas (ES/EN/PT), demo animada, precios con MercadoPago |
| [`desktop/`](desktop/) | **Programa de PC profesional** (Electron + React) con instalador NSIS `.exe` para Windows |
| [`app-python/`](app-python/) | **Versión autoinstalable** (`INICIAR_MVSQL.bat`): un doble clic instala todo y abre la app (Streamlit) |
| [`docs/`](docs/) | Plan de negocio, análisis de competencia, guion del video demo, integración MercadoPago |

## ✨ Funciones principales

- 💬 **Lenguaje natural → SQL** en ES/EN/PT, con JOINs correctos según las relaciones reales del esquema
- 🤖 **IA a elección del cliente**: Claude, GPT, Gemini, Groq, Mistral, DeepSeek, Grok, **Ollama local (gratis)** o cualquier endpoint OpenAI-compatible — con API key propia o con créditos facturados por nosotros
- 🗄️ **Multi-base**: SQL Server, MySQL/MariaDB, PostgreSQL y SQLite — se adapta a cualquier esquema sin configuración
- 🚀 **Optimización con CTE**: consultas estructuradas con `WITH … AS`, filtros tempranos, sin `SELECT *`; re-optimizador de SQL existente
- 📐 **Intervalo de confianza** en cada respuesta (ej. 92% ±5), combinando autoevaluación del modelo, señal RAG y validación estructural
- 🛡️ **Anti-alucinación**: el SQL se valida contra el catálogo real; si algo no existe se rechaza y se auto-corrige (self-repair)
- 🔒 **Seguridad**: conexión read-only, solo `SELECT`/`WITH`; el RAG es local — los datos nunca salen de tu red, solo viaja el esquema
- ⭐ **Consultas guardadas** con nombre + conversión a **stored procedures** de producción
- 📊 **Gráficos automáticos** (línea/barras/dispersión/torta) + análisis en lenguaje natural
- ⬇️ **Exportación** a Excel (con formato), CSV, PDF y HTML

## 🚀 Inicio rápido

**Versión autoinstalable (Windows, 2 minutos):** entrá a `app-python/` y hacé
doble clic en **`INICIAR_MVSQL.bat`**. Instala Python/dependencias, genera una
base demo y abre la app en el navegador.

**App de escritorio (desarrollo):**
```bash
cd desktop && npm install && npm run dev      # desarrollo
npm run dist                                   # instalador .exe (Windows)
```

**Web (Vercel):** importar el repo en Vercel con *Root Directory* = `web/`
(es un sitio estático, sin build).

## 💰 Modelo comercial

Suscripción (US$ 15/29/79 por mes con API key propia) **o** paquetes de
créditos (US$ 9/35/110) donde nosotros ponemos la IA y la facturamos.
Prueba completa de 3 días sin tarjeta. Pagos por MercadoPago.
Detalle completo en [`docs/PLAN_DE_NEGOCIO.md`](docs/PLAN_DE_NEGOCIO.md).
