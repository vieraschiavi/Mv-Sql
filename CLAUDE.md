# CLAUDE.md — MV SQL NLP

Guía para Claude Code al trabajar en este repo. Leela antes de tocar código.

## Qué es

**MV SQL NLP** ("Tu base de datos, en tu idioma") es una suite que convierte lenguaje
natural (español/inglés/portugués) en SQL: la IA genera el SQL (con CTEs, sin `SELECT *`),
lo valida contra el catálogo real del esquema (anti-alucinación), ejecuta en modo
**solo lectura** y devuelve tablas, gráficos y análisis exportables. Soporta SQLite, SQL
Server, MySQL/MariaDB y PostgreSQL, y deja elegir el proveedor de IA (Claude, GPT, Gemini,
Groq, Mistral, DeepSeek, Grok u Ollama local). Es un monorepo con tres productos separados:
landing/pagos web (`web/`), app de escritorio Electron+React (`desktop/`) y app
autoinstalable Python/Streamlit (`app-python/`). No es un producto para escribir en la base
del cliente: nunca ejecuta INSERT/UPDATE/DELETE/DDL.

## Stack

- **`web/`** — Node.js. Landing trilingüe (ES/EN/PT) + funciones serverless en `web/api/*.js`
  (MercadoPago: preferencia, suscripción, webhook, emisión y descarga de licencia). Deploy en
  Vercel, sin build (HTML/CSS/JS estático). Deps clave: `jsonwebtoken`, `jszip`, `mercadopago`,
  `@vercel/kv` (opcional).
- **`desktop/`** — Electron + React 18 + Vite. App de escritorio para Windows con instalador
  NSIS (`electron-builder`). Conectores nativos: `better-sqlite3`, `mssql`, `mysql2`, `pg`.
  Export a Excel/PDF con `xlsx`, `jspdf`.
- **`app-python/`** — Python 3 + Streamlit (`app.py`, puerto fijo `8791`). El motor real:
  `motor.py` (generación/validación de SQL), `conectores.py` (conexión multi-motor, siempre
  read-only), `catalogo.py` (extracción de esquema), `proveedores_ia.py` (multi-proveedor de
  IA), `equipo.py`/`auditoria.py` (PIN por usuario, permisos por rol, log de auditoría),
  `cuadernos.py` (informes reutilizables con variables), `esquema_visual.py` (diagrama de
  relaciones + plan de ejecución), `exportar.py` (Excel/CSV/PDF/HTML/JSON). Deps en
  `app-python/requirements.txt` (streamlit, pandas, plotly, scikit-learn, shap, pyarrow,
  openpyxl, reportlab, faker; conectores de BD como `pyodbc`/`pymysql`/`psycopg2-binary` son
  opcionales, comentados en el archivo).
- **Tests**:
  - `web/tests/*.test.js` — Node nativo (`assert` + mocks), sin framework.
  - `app-python/tests/test_*.py` — scripts standalone con runner propio (`test()` decorator
    interno), sin pytest ni unittest.
  - `desktop/` no tiene tests configurados.

## Comandos

| Objetivo | Comando |
|---|---|
| Instalar deps de `web/` | `cd web && npm install` |
| Tests de `web/` | `cd web && npm test` (descubre y corre todos los `tests/*.test.js`) |
| Instalar deps de `desktop/` | `cd desktop && npm install` |
| Correr `desktop/` en desarrollo | `cd desktop && npm run dev` |
| Build del instalador `desktop/` (Windows) | `cd desktop && npm run dist` (o `npm run dist:portable`) |
| Instalar deps de `app-python/` | `pip install -r app-python/requirements.txt` |
| Correr la app Python (Streamlit) | `cd app-python && streamlit run app.py` (abre en `http://localhost:8791` vía `INICIAR_MVSQL.bat` en Windows) |
| Tests de `app-python/` | `cd app-python && for f in tests/test_*.py; do python3 "$f" || break; done` (o `npm test` en la raíz, que descubre estos + los de `web/` sin listarlos a mano) |
| Lint / format | no hay — no introduzcas uno sin que te lo pidan |

> No hay `package.json` de test en `desktop/`; no inventes uno. El repo raíz solo reexporta
> `npm test` hacia `web/` (ver `package.json` de la raíz, usado por Vercel para publicar desde
> la raíz con `outputDirectory: web`).

## Estructura

```
├── web/                  landing trilingüe (ES/EN/PT) + api/*.js serverless (MercadoPago) — deploy Vercel
├── desktop/               app de escritorio Electron + React (Vite), instalador NSIS Windows
├── app-python/            producto autoinstalable Streamlit: motor.py, conectores.py, catalogo.py,
│                          proveedores_ia.py, equipo.py/auditoria.py, cuadernos.py, esquema_visual.py,
│                          exportar.py, generar_db_demo.py, tests/
├── api/                   copia de las funciones serverless de pago (espejo de web/api, usado por Vercel raíz)
├── docs/                  plan de negocio, guiones de venta ES/EN/PT, checklist de despliegue, MercadoPago
├── installer/             mvsql.nsi — instalador NSIS del producto Python (Windows, no corre en Linux)
├── tools/                 empaquetado (zip) y generación del video demo
├── .github/workflows/     build-desktop.yml — compila el .exe en runner Windows al taggear v*
├── package.json           raíz: solo reexporta test hacia web/ (Vercel publica desde acá)
└── vercel.json            config de deploy raíz (outputDirectory: web)
```

## Flujo de trabajo

1. **Plan** — ante un cambio no trivial, planificá primero (`/plan`). Solo lectura hasta aprobar.
2. **Cambio** — editá el mínimo necesario. Respetá la separación `web/` (pagos/landing) vs.
   `desktop/` (Electron/React) vs. `app-python/` (motor NL-a-SQL + Streamlit).
3. **Test** — corré el/los test(s) del subproyecto que tocaste (`/test`). No declares éxito sin
   correrlos y pegar la salida.
4. **Ship** — `/ship`: test → commit descriptivo → push a la rama de trabajo → PR draft.

## Convenciones

- **Solo lectura / solo `SELECT` o `WITH`**: toda conexión a BD se abre en modo read-only
  (`conectores.py`: `pyodbc readonly=True`, `psycopg2 set_session(readonly=True)`) y `motor.py`
  rechaza SQL que no empiece con `SELECT`/`WITH` — nunca INSERT/UPDATE/DELETE/DROP/ALTER/EXEC.
  No relajes esto sin que te lo pidan explícitamente.
- **Anti-alucinación**: el SQL generado se valida contra el catálogo real del esquema
  (`catalogo.py`) antes de ejecutarse; si referencia algo que no existe, se rechaza y se
  autocorrige. No agregues un camino de ejecución que se salte esa validación.
- **Trilingüe (ES/EN/PT)** en toda la superficie de usuario: `web/` (`index.html`, `en/`,
  `pt/`), `desktop/src/i18n.js`, `app-python/app.py` (diccionario `T`). Si agregás un texto
  nuevo de cara al usuario, agregalo en los 3 idiomas.
- **Secretos nunca en el código**: credenciales de BD (usuario/password/servidor) y API keys de
  proveedores de IA (Claude/GPT/Gemini/etc.) viajan por parámetro, `.env` o config del usuario
  — nunca hardcodeadas ni commiteadas. No hay `.env.example` en el repo; los nombres de
  variables sensibles están documentados en `docs/DESPLIEGUE.md` y `docs/INTEGRACION_MERCADOPAGO.md`.
- **Multi-motor sin romper la interfaz común**: `conectores.py` expone la misma interfaz
  (`conectar()` → `extraer_catalogo()` → `ejecutar(sql, limite)`) para SQLite/SQL
  Server/MySQL/PostgreSQL; cualquier conector nuevo debe respetarla para no romper el resto del
  sistema (RAG, generación, validador, UI).
- **Permisos por rol**: `equipo.py` da acceso por PIN y cada usuario ve solo las tablas de su
  rol (la IA ni se entera de que existen las demás); `auditoria.py` registra quién consultó qué.
  No expongas tablas fuera del alcance del rol al generar o validar SQL.

## Do / Don't

**Do**
- Correr los tests del subproyecto tocado antes de cerrar cualquier cambio.
- Mantener la paridad ES/EN/PT en cada string nuevo.
- Usar `git status` / `git diff` para revisar antes de commitear.
- Respetar la interfaz común de `conectores.py` si agregás o tocás un motor de BD.

**Don't**
- No agregues ni habilites ejecución de SQL que no sea `SELECT`/`WITH` (nada de DDL/DML).
- No commitees `.env`, credenciales de BD, API keys de proveedores de IA, tokens de MercadoPago
  ni artefactos de build (`node_modules/`, `desktop/dist/`, `desktop/release/`, `.venv/`).
- No corras el build de NSIS/electron-builder ni el `.bat` en este entorno Linux.
- No introduzcas un linter o framework de test nuevo sin que te lo pidan.
- No uses `git push --force` ni `rm -rf`.

## Agentes disponibles

`explorer` (mapear el repo) · `planificador` (plan antes de cambiar) · `parallel-worker` (fan-out)
· `especialista` (NL-a-SQL multi-base y multi-proveedor de IA) · `revisor` (review del diff)
· `verificador` (gate de evidencia).

## Contexto / Compact

- Empezá por este archivo y el `README.md` (hay versiones ES/EN/PT).
- Para mapear a lo ancho, delegá en `explorer` en vez de leer todo en el hilo principal.
- Si el contexto se llena, compactá reteniendo: la tabla de comandos, la regla de solo-lectura
  + anti-alucinación, la regla trilingüe, y qué archivos/subproyecto tocaste.
