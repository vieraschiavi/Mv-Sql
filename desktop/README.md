# MV SQL NLP — App de escritorio (Electron + React)

Programa profesional para Windows: consultá cualquier base SQL en lenguaje
natural, con IA a elección del cliente, intervalo de confianza, consultas
guardadas, stored procedures, optimización CTE y exportación Excel/CSV/PDF/HTML.

## Desarrollo

```bash
npm install
npm run dev          # Vite + Electron con hot-reload
```

## Generar el instalador profesional (.exe)

**Opción recomendada — GitHub Actions (automático, sin instalar nada):**
el repo incluye `.github/workflows/build-desktop.yml`, que compila en un
runner Windows real (con toolchain nativo completo, sin las limitaciones
de compilar cruzado desde Linux/Mac). Se dispara solo:
- Al pushear un tag `v*` (ej. `git tag v1.0.0 && git push origin v1.0.0`)
- O manualmente desde la pestaña **Actions → Build Windows desktop installer → Run workflow**

Sube automáticamente el instalador NSIS, la versión portable y el zip como
assets del Release de GitHub.

**Opción local (requiere Windows real, o Linux/Mac + Wine):**

```bash
npm install
npm run dist         # → release/MV-SQL-NLP-Setup-1.0.0.exe (instalador NSIS)
npm run dist:portable  # → .exe portable, sin instalación
```

Compilar cruzado desde Linux sin Windows/Wine **no funciona**: el módulo
nativo de SQLite (better-sqlite3) no se puede compilar para Windows sin un
toolchain de Windows, y el propio binario de Electron para win32-x64 hay
que descargarlo desde GitHub Releases. Por eso conviene la opción de
GitHub Actions de arriba.

El instalador NSIS incluye: elección de carpeta, accesos directos de
escritorio y menú inicio, desinstalador, idiomas ES/EN/PT y EULA.

> **Icono:** ya incluido en `build/icon.ico` (generado programáticamente;
> reemplazalo por un logo definitivo cuando lo tengas).
> **Firma de código:** para distribución comercial configurar
> `CSC_LINK`/`CSC_KEY_PASSWORD` (certificado .pfx) — evita las advertencias
> de SmartScreen.
> **Auto-update:** ya está configurado `publish: github` — al publicar un
> release en GitHub, la app puede actualizarse con electron-updater.

## Arquitectura

```
electron/main.cjs            proceso principal (ventana + IPC)
electron/preload.cjs         puente seguro (contextBridge)
electron/services/db.cjs     conector universal: SQLite, SQL Server, MySQL, PostgreSQL
electron/services/ai.cjs     multi-proveedor IA: Claude/GPT/Gemini/Groq/Mistral/DeepSeek/Grok/Ollama/custom
electron/services/engine.cjs motor NL2SQL: retrieval + generación + validador + confianza + self-repair
electron/services/store.cjs  persistencia local (consultas guardadas, preferencias)
src/                         React (Vite): UI en ES/EN/PT, gráficos Recharts, exports
```

Seguridad: conexiones read-only, solo SELECT/WITH (validador en 3 capas),
la API key queda en la máquina del usuario, los datos nunca salen de su red.
