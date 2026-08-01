# ⚡ MV SQL NLP

🌎 Languages: [Español](README.md) · **English** · [Português](README.pt.md)

**Your database, in your own words.** Query any SQL database in natural language
(Spanish, English or Portuguese), without writing a line of code. The AI
generates optimised, professional SQL with CTEs, validates it against your real
schema, shows you the **confidence interval** of every answer and returns tables,
charts and analysis exportable to Excel, CSV, PDF and HTML.

## 📦 What's in this repository

| Folder | What it is |
|---|---|
| [`web/`](web/) | Commercial landing page (dark SaaS style) ready for **Vercel** — 3 languages (ES/EN/PT), animated demo, pricing with MercadoPago |
| [`desktop/`](desktop/) | **Professional desktop program** (Electron + React) with an NSIS `.exe` installer for Windows |
| [`app-python/`](app-python/) | **Self-installing version** (`INICIAR_MVSQL.bat`): one double-click installs everything and opens the app (Streamlit) |
| [`docs/`](docs/) | Business plan and financial model, sales material (demo script, proposal, one-pager) in 3 languages, deployment checklist, MercadoPago integration |

## ✨ Main features

- 💬 **Natural language → SQL** in ES/EN/PT, with correct JOINs based on the real relationships in the schema
- 🤖 **The AI the client chooses**: Claude, GPT, **Copilot (Azure OpenAI)**, Gemini, Groq, Mistral, DeepSeek, Grok, **local Ollama (free)** or any OpenAI-compatible endpoint — with their own API key or with credits billed by us
- 🗄️ **Multi-database**: SQL Server, MySQL/MariaDB, PostgreSQL and SQLite — adapts to any schema with no configuration
- 📄 **File mode**: query a **CSV, Excel or Parquet** with no database at all — fast cached loading
- 🔢 **Number format on demand**: decimals, thousands separator, % and **currency** ($U, US$, AR$, R$, €…) applied to tables, charts and analysis
- 🧩 **MCP connector**: `CONECTAR_CLAUDE_MCP.bat` wires your **Claude Desktop** straight to your database (SQL Server/MySQL/PostgreSQL/SQLite) over MCP
- 🚀 **CTE optimisation**: structured queries with `WITH … AS`, early filters, no `SELECT *`; re-optimiser for existing SQL
- 📐 **Confidence interval** on every answer (e.g. 92% ±5), combining the model's self-assessment, the RAG signal and structural validation
- 🛡️ **Anti-hallucination**: the SQL is validated against the real catalogue; anything that doesn't exist is rejected and self-repaired
- 🔒 **Security**: read-only connection, `SELECT`/`WITH` only; the RAG runs locally — the data never leaves your network, only the schema travels
- 👥 **Team and permissions**: each user logs in with their PIN and sees **only the tables for their role** — the AI never learns the others exist
- 🛡️ **Audit trail**: who queried what, when, with which SQL and with what result — exportable to CSV for compliance
- ⭐ **Saved queries** with a name + conversion into production **stored procedures**
- 📓 **Notebooks**: reusable reports mixing Markdown, questions and SQL with **shared variables** (`{{month}}`, `{{branch}}`) — run the whole thing again by changing one value, export to Markdown
- 🕸️ **Relationship diagram**: the map of your tables and their foreign keys, plus the tables left dangling
- ⚙️ **Execution plan explained**: why a query is slow, in plain language, with the concrete recommendation
- 🔍 **Explore panel (EDA)**: correlation map between variables + **variable influence** (Random Forest) to see what drives what — over the result or over any full table
- 📊 **Professional charts**: labelled axes, formatted values that never overlap, type chosen automatically from the data or by hand (bars, horizontal bars, line, area, pie, scatter, histogram) + natural-language analysis
- ⬇️ **Export** to Excel (formatted), CSV, **JSON**, PDF and HTML
- 🔐 Optional **SSH tunnel** for databases that aren't exposed to the internet

## 🚀 Quick start

**Self-installing version (Windows, 2 minutes):** go into `app-python/` and
double-click **`INICIAR_MVSQL.bat`**. It installs Python and the dependencies,
generates a demo database and opens the app at `http://localhost:8791` (fixed
port, so it won't collide with other apps running on your PC).

> ⚠️ If you had already downloaded an older copy of the program (for example
> from the original sample zip), download it again — old versions had a known
> pandas bug when displaying date columns (`AssertionError` in `pd.to_datetime`),
> already fixed here.

**Desktop app (development):**
```bash
cd desktop && npm install && npm run dev      # development
npm run dist                                   # .exe installer (Windows)
```

**Web (Vercel):** import the repo in Vercel with *Root Directory* = `web/`
(it's a static site, no build step).

## ✅ Running the tests (on a clean machine)

With just `git` and `node` (18+) you can run the `web/` tests; if `python3`
is also on your `PATH` it runs the NL-to-SQL engine tests too
(`app-python/tests/` needs none of the packages in `requirements.txt`, only
the standard library):

```bash
git clone https://github.com/vieraschiavi/Mv-Sql.git
cd Mv-Sql
npm ci        # only installs web/'s deps (jsonwebtoken, mercadopago, jszip…)
npm test      # discovers and runs EVERYTHING: web/tests/*.test.js + app-python/tests/test_*.py
```

Exits with a non-zero status if anything fails — the same thing
`.github/workflows/tests.yml` runs on every push. To run a subset:
`npm test -- --web` or `npm test -- --python`.

## 💰 Commercial model

**The service is the business; the product is the differentiator.**

| What | Price | How it's charged |
|---|---|---|
| **Implementation** on your DB/ERP | US$ 2,500 (Express US$ 900) | one-time |
| Monthly licence | US$ 15 / 29 / 79 | subscription (MercadoPago preapproval) |
| Support and maintenance | US$ 150/month | subscription |
| Embedded AI credits | US$ 9 / 35 / 110 | one-time |

Full 7-day trial, no credit card. Market, competition and profitability analysis
in [`docs/PLAN_DE_NEGOCIO.md`](docs/PLAN_DE_NEGOCIO.md); runnable financial model
in [`docs/MODELO_NEGOCIO.py`](docs/MODELO_NEGOCIO.py). Production checklist in
[`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

Sales material in English: [demo script](docs/VENTA_GUION_DEMO_EN.md) ·
[proposal](docs/VENTA_PROPUESTA_EN.md) · [one-pager](docs/VENTA_ONEPAGER_EN.md).
