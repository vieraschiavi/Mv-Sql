// MV SQL NLP — proceso principal de Electron
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");

const db = require("./services/db.cjs");
const engine = require("./services/engine.cjs");
const store = require("./services/store.cjs");

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 980,
    minHeight: 640,
    backgroundColor: "#0b1220",
    autoHideMenuBar: true,
    title: "MV SQL NLP",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.VITE_DEV) {
    win.loadURL("http://localhost:5173");
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

// ── IPC: base de datos ─────────────────────────────────────────
ipcMain.handle("db:connect", async (_e, cfg) => {
  const catalog = await db.connect(cfg);
  engine.setCatalog(catalog, db.dialect());
  return { tables: Object.keys(catalog.tablas).length, catalog };
});

ipcMain.handle("db:pick-sqlite", async () => {
  const r = await dialog.showOpenDialog(win, {
    title: "Elegir base SQLite",
    filters: [{ name: "SQLite", extensions: ["db", "sqlite", "sqlite3"] }],
    properties: ["openFile"],
  });
  return r.canceled ? null : r.filePaths[0];
});

// ── IPC: consulta NL → SQL → resultado ─────────────────────────
ipcMain.handle("query:ask", async (_e, { question, ai, options }) => {
  return engine.answer(question, ai, {
    run: (sql, limit) => db.run(sql, limit),
    ...options,
  });
});

ipcMain.handle("query:run-sql", async (_e, { sql }) => {
  engine.assertReadOnly(sql);
  return db.run(sql, 5000);
});

ipcMain.handle("query:stored-procedure", (_e, { sql, name, ai }) =>
  engine.storedProcedure(sql, name, ai));

ipcMain.handle("query:optimize", (_e, { sql, ai }) => engine.optimize(sql, ai));

ipcMain.handle("ai:test", (_e, ai) => engine.testProvider(ai));

// ── IPC: consultas guardadas + configuración (persistencia local) ──
ipcMain.handle("store:get", (_e, key) => store.get(key));
ipcMain.handle("store:set", (_e, { key, value }) => store.set(key, value));

// ── IPC: guardar archivo exportado ─────────────────────────────
ipcMain.handle("file:save", async (_e, { defaultName, dataBase64, filters }) => {
  const r = await dialog.showSaveDialog(win, { defaultPath: defaultName, filters });
  if (r.canceled) return null;
  fs.writeFileSync(r.filePath, Buffer.from(dataBase64, "base64"));
  return r.filePath;
});
