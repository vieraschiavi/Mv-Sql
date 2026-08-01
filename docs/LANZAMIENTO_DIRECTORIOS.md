# 🚀 Listado en directorios — Product Hunt · G2 · AlternativeTo

Paquete listo para pegar. Cada bloque está redactado en el idioma y el largo
que pide la plataforma, y **solo dice cosas que el código hace de verdad** —
la lista de lo verificable está al final, para que no se cuele una promesa
que después no aguanta una demo.

> **Lo que no puedo hacer yo:** las tres plataformas piden cuenta a tu nombre
> como *maker* y las capturas las tenés que sacar vos de la app corriendo con
> datos reales (o con la base demo). El texto está resuelto acá; lo que queda
> es abrir la cuenta, pegar y subir imágenes.

---

## Orden recomendado

No los lances el mismo día.

1. **AlternativeTo** primero — no tiene "día de lanzamiento", acepta el
   listado cuando quieras, y te da un backlink y una URL canónica que las
   otras dos van a pedir como referencia.
2. **G2** segundo — la ficha tarda días en aprobarse y necesita al menos una
   reseña real para salir del limbo. Como `web/assets/resenas.json` está
   vacío a propósito (cero contenido inventado), esto depende de que un
   cliente de la implementación deje la primera. Es el cuello de botella
   real: arrancalo temprano aunque publique tarde.
3. **Product Hunt** último y con fecha elegida — es el único con efecto de
   un solo día. Martes a jueves, 00:01 PST (= 05:01 UTC = **02:01 en
   Montevideo**). Lanzar un lunes o un viernes desperdicia el envión.

---

## 1. Product Hunt

**Name**
```
MV SQL NLP
```

**Tagline** (60 caracteres máx — este entra en 57)
```
Ask your SQL database in plain English. Runs on your PC.
```

**Description** (~260 caracteres)
```
Query SQL Server, PostgreSQL, MySQL or SQLite in plain language. The AI writes
the SQL, validates it against your real schema so it can't hallucinate tables,
and runs it read-only. Your data never leaves your network — only the schema
does. Bring your own AI key or run Ollama locally.
```

**Topics**: `Developer Tools` · `Artificial Intelligence` · `SQL` ·
`Data Visualization` · `Productivity`

**First comment del maker** (esto es lo que más se lee — contá el problema,
no las features):
```
Hi PH 👋

I spent years in collections analytics watching the same thing happen: someone
needs a number, they ask IT, and three days later they get a spreadsheet that
answers a slightly different question.

The obvious fix is "connect an LLM to the database", but every time I tried it
in a real company it fell over on the same three things:

1. It invents tables. Confidently. With correct-looking SQL.
2. It can write. Nobody is letting an LLM near production with write access.
3. Everyone with the connection string sees the entire database, and there is
   no record of who asked what.

MV SQL NLP is my answer to those three, and only those three:

- Every generated query is validated against the real schema catalog before it
  runs. Reference a column that doesn't exist and it's rejected and re-written.
- Read-only is enforced at the point of execution, not just in the prompt —
  the connection itself is opened read-only and non-SELECT statements are
  blocked in the connector, so no code path can bypass it.
- Each person logs in with a PIN and only sees the tables their role allows.
  The AI is never told the other tables exist. Every query is logged.

It runs on your machine — Windows installer or Python. Your rows never go to
the model; only the schema does. You bring your own key (Claude, GPT, Gemini,
Groq, Mistral, DeepSeek, Grok, Azure OpenAI) or point it at a local Ollama and
pay nothing for inference.

Free for 7 days, no card. Built in Uruguay 🇺🇾, works in Spanish, English and
Portuguese — interface and answers.

Happy to answer anything, especially the skeptical questions. Those are the
useful ones.
```

**Links**: web `https://mvsqlnlp.com` · GitHub `https://github.com/vieraschiavi/Mv-Sql`

**Media** (lo que tenés que subir vos):
- Thumbnail 240×240 — sacá el ⚡ de `web/assets/og-image.png`
- Gallery 1270×760, mínimo 3: (1) pregunta en lenguaje natural → SQL generado
  con el intervalo de confianza; (2) tabla + gráfico del resultado; (3)
  diagrama de relaciones o el panel de equipo/auditoría, que es el
  diferenciador que nadie más muestra.
- El video: `web/assets/video/demo_en.mp4` ya existe y está en inglés.
  Es vertical (1080×1920) porque se hizo para WhatsApp/Instagram — para PH
  conviene reencuadrarlo horizontal o subirlo igual como secundario.

---

## 2. G2

**Product Name**: `MV SQL NLP`

**Categories**: `Natural Language Processing (NLP) Software` ·
`Business Intelligence` · `Data Analysis`

**Short description** (~150 caracteres)
```
Natural-language querying for SQL databases. Schema-validated, read-only, runs
on-premise with the AI provider of your choice.
```

**Full description**
```
MV SQL NLP turns questions in plain language into professional SQL — with CTEs,
correct JOINs based on your real foreign keys, and no SELECT *. It connects to
SQL Server, PostgreSQL, MySQL/MariaDB and SQLite, and adapts to any schema with
no configuration or data migration.

Three things make it usable in a company rather than a demo:

Anti-hallucination. Generated SQL is validated against the actual schema catalog
before execution. If it references a table or column that doesn't exist, it's
rejected and automatically corrected, not run.

Read-only by construction. The database connection is opened in read-only mode
and non-SELECT statements are blocked at the point of execution, inside the
connector every code path goes through — not only in the prompt or the
orchestrator. MV SQL NLP never issues INSERT, UPDATE, DELETE or DDL.

Roles and audit. Each user logs in with a PIN and sees only the tables their
role permits — the AI is never shown the rest, so it cannot query them even by
mistake. Every question, the SQL it produced and its outcome are logged and
exportable to CSV for compliance.

It runs on your infrastructure. Your rows never leave your network; only the
schema is sent to the model. You use your own API key (Claude, GPT, Azure
OpenAI, Gemini, Groq, Mistral, DeepSeek, Grok) or a local Ollama instance at
zero inference cost.

Results come back as tables, charts and written analysis, exportable to Excel,
CSV, PDF, HTML and JSON. Includes reusable notebooks with shared variables,
relationship diagrams, interpreted execution plans, and an exploratory analysis
panel with correlation maps and variable influence.

Interface and answers in Spanish, English and Portuguese.
```

**Pricing** (dejalo explícito — G2 penaliza el "contact us"):
| Plan | Precio | Nota |
|---|---|---|
| Free trial | US$ 0 | 7 días, sin tarjeta |
| Personal / Professional / Business | US$ 15 / 29 / 79 por mes | con tu propia clave de IA |
| Créditos de IA embebidos | US$ 9 / 35 / 110 | pago único, sin suscripción |
| Implementación | US$ 2.500 (Express US$ 900) | pago único, sobre tu BD/ERP |

**Lo que G2 te va a pedir y todavía no tenés**: al menos una reseña
verificada. Pedísela al primer cliente de implementación — no la escribas
vos, y no la inventes. `resenas.json` está vacío a propósito y conviene que
siga siendo un reflejo honesto.

---

## 3. AlternativeTo

**Name**: `MV SQL NLP`

**Description** (~200 caracteres)
```
Desktop app that turns plain-language questions into validated SQL for SQL
Server, PostgreSQL, MySQL and SQLite. Read-only, runs locally, works with any
AI provider including local Ollama.
```

**Categories**: `Development` → `Database Tools`, `Office & Productivity` →
`Business Intelligence`

**Platforms**: `Windows` (instalador NSIS) · `Self-Hosted` (Python/Streamlit,
corre en Linux y Mac) · `Mac` y `Linux` solo si vas a soportarlas de verdad —
la app Python corre, pero el instalador de un clic es Windows. No marques lo
que no vas a bancar.

**License**: `Commercial` — con `Free Trial`

**Alternative to** (así es como te encuentran; poné las que de verdad
compiten):
`Text2SQL.ai` · `AI2sql` · `Vanna.ai` · `Julius AI` · `SeekTable` ·
`Metabase` (por el "preguntá en lenguaje natural", aunque Metabase es
mucho más ancho)

**Features a tildar/agregar**: `Natural Language Processing` ·
`SQL support` · `Works Offline` · `Privacy focused` · `Self-Hosted` ·
`No Cloud Required` · `Multilingual` · `Export to Excel` · `Data
Visualization`

---

## Lo que se puede afirmar (verificado contra el código)

Cualquier cosa que agregues a estos textos, verificala igual antes.

| Afirmación | Dónde se verifica |
|---|---|
| 4 motores: SQL Server, PostgreSQL, MySQL/MariaDB, SQLite | `app-python/conectores.py` — un `conectar()` por motor |
| 10 proveedores de IA + endpoint OpenAI-compatible propio | `app-python/proveedores_ia.py` — anthropic, openai, azure, gemini, groq, mistral, deepseek, xai, ollama, custom |
| Solo lectura, solo `SELECT`/`WITH` | `conectores.py:asegurar_solo_lectura()` + `tests/test_solo_lectura.py` (22 casos, incluye inyección directa) |
| Validación contra el catálogo real | `app-python/catalogo.py` + `motor.py:validar_sql()` |
| Roles por PIN, la IA no ve las tablas de otros roles | `app-python/equipo.py:tablas_visibles()` + `tests/test_equipo_auditoria.py` |
| Auditoría exportable a CSV | `app-python/auditoria.py` |
| Trial de 7 días | `app-python/licencia.py:TRIAL_DIAS` + `tests/test_licencia.py` (18 casos) |
| Export a Excel/CSV/PDF/HTML/JSON | `app-python/exportar.py` |
| Cuadernos con variables compartidas | `app-python/cuadernos.py` |
| Diagrama de relaciones y plan de ejecución | `app-python/esquema_visual.py` |
| Trilingüe en interfaz y respuestas | `app.py` (dict `T`), landing 157/157 claves en EN y PT |
| Túnel SSH | `conectores.py` (opcional, requiere `sshtunnel`) |
| Conector MCP para Claude Desktop | `app-python/CONECTAR_CLAUDE_MCP.bat` |

## Lo que NO se puede afirmar todavía

No lo pongas en ningún listado hasta que sea cierto:

- **"Integración con SAP / Odoo / Dynamics"** — MV SQL NLP conecta al *motor
  de base de datos* sobre el que corren esos sistemas, no al ERP por API. La
  landing ya lo dice con esa precisión; mantené la misma redacción acá.
- **Cantidad de clientes, empresas o países** — no hay ninguno público
  todavía. Un número inventado en G2 es exactamente lo que un comprador
  técnico verifica primero.
- **Reseñas o testimonios** — `resenas.json` está vacío a propósito.
- **"Compatible con Mac/Linux"** como producto instalable — la app Python
  corre, pero no hay instalador ni se probó end-to-end en esas plataformas.
