/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — proceso principal de Electron
const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const path = require("path");
const fs = require("fs");

const db = require("./services/db.cjs");
const engine = require("./services/engine.cjs");
const store = require("./services/store.cjs");
const licencia = require("./services/licencia.cjs");

let win;

// ── Puerta de acceso ───────────────────────────────────────────
// Los textos van acá y no en src/i18n.js porque el diálogo se muestra
// ANTES de que exista ventana: no hay React todavía para traducirlo.
const T = {
  es: {
    titulo: "Se terminó la prueba",
    cuerpo: "Los 7 días de prueba de MV SQL NLP terminaron.",
    detalle: "Comprá tu licencia en mvsqlnlp.com y, cuando la recibas por email, " +
      "elegí \"Ya tengo una licencia\" para activarla.",
    comprar: "Comprar licencia",
    tengo: "Ya tengo una licencia",
    salir: "Salir",
    elegir: "Elegir el archivo de licencia",
    malaTitulo: "Esa licencia no sirve",
    malaFormato: "El archivo no es una licencia válida de MV SQL NLP.",
    malaVencida: "Esa licencia está vencida.",
  },
  en: {
    titulo: "Your trial has ended",
    cuerpo: "The 7-day MV SQL NLP trial has ended.",
    detalle: "Buy your licence at mvsqlnlp.com and, once it arrives by email, " +
      "choose \"I already have a licence\" to activate it.",
    comprar: "Buy a licence",
    tengo: "I already have a licence",
    salir: "Quit",
    elegir: "Choose the licence file",
    malaTitulo: "That licence doesn't work",
    malaFormato: "The file is not a valid MV SQL NLP licence.",
    malaVencida: "That licence has expired.",
  },
  pt: {
    titulo: "Seu teste terminou",
    cuerpo: "Os 7 dias de teste do MV SQL NLP terminaram.",
    detalle: "Compre sua licença em mvsqlnlp.com e, quando ela chegar por email, " +
      "escolha \"Já tenho uma licença\" para ativá-la.",
    comprar: "Comprar licença",
    tengo: "Já tenho uma licença",
    salir: "Sair",
    elegir: "Escolher o arquivo de licença",
    malaTitulo: "Essa licença não serve",
    malaFormato: "O arquivo não é uma licença válida do MV SQL NLP.",
    malaVencida: "Essa licença está vencida.",
  },
};

function textos() {
  const guardado = store.get("lang");
  return T[guardado] || T.es;
}

/**
 * Corre antes de abrir la ventana. Devuelve false si hay que cerrar.
 *
 * Es un diálogo nativo y no una pantalla de React a propósito: si el
 * acceso se chequeara adentro de la ventana, la app ya estaría cargada
 * y bastaría con no pedirle nada al backend para seguir usándola.
 */
async function puertaDeAcceso() {
  // Antes de decidir nada: si la licencia esta por vencer y la
  // suscripcion sigue paga, se pide una nueva. Va ACA y no despues
  // porque el que paga todos los meses no tiene que ver ni una vez el
  // cartel de "compra tu licencia". No lanza nunca y tiene su propio
  // limite de espera: sin red, la app abre igual con lo que ya tenia.
  await licencia.renovarSiCorresponde();

  let estado = licencia.verificarAcceso();
  while (!estado.permitido) {
    const t = textos();
    const r = await dialog.showMessageBox({
      type: "warning",
      title: "MV SQL NLP",
      message: t.cuerpo,
      detail: t.detalle,
      buttons: [t.comprar, t.tengo, t.salir],
      defaultId: 0,
      cancelId: 2,
    });

    if (r.response === 2) return false;

    if (r.response === 0) {
      await shell.openExternal("https://mvsqlnlp.com/#precios");
      // No se corta: al volver de comprar, el usuario sigue con el
      // diálogo abierto para activar la licencia que le llegó.
      continue;
    }

    const elegido = await dialog.showOpenDialog({
      title: t.elegir,
      filters: [{ name: "Licencia MV SQL NLP", extensions: ["json"] }],
      properties: ["openFile"],
    });
    if (elegido.canceled) continue;

    let res;
    try {
      res = licencia.instalarLicencia(fs.readFileSync(elegido.filePaths[0], "utf8"));
    } catch {
      res = { ok: false, motivo: "formato" };
    }
    if (!res.ok) {
      await dialog.showMessageBox({
        type: "error",
        title: t.malaTitulo,
        message: res.motivo === "vencida" ? t.malaVencida : t.malaFormato,
      });
    }
    estado = licencia.verificarAcceso();
  }
  return true;
}

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

app.whenReady().then(async () => {
  if (await puertaDeAcceso()) createWindow();
  else app.quit();
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

// La UI lo usa para el aviso de "te quedan N días" y para el botón de
// comprar. No vuelve a chequear nada: la puerta ya se cruzó arriba.
ipcMain.handle("licencia:estado", () => licencia.verificarAcceso());

// ── IPC: base de datos ─────────────────────────────────────────
ipcMain.handle("db:connect", async (_e, cfg) => {
  const catalog = await db.connect(cfg);
  engine.setCatalog(catalog, db.dialect());
  return { tables: Object.keys(catalog.tablas).length, catalog };
});

ipcMain.handle("db:pick-archivos", async () => {
  const r = await dialog.showOpenDialog(win, {
    title: "Elegir archivos Excel o CSV",
    filters: [
      { name: "Excel y CSV", extensions: ["xlsx", "xls", "xlsm", "csv", "txt", "tsv"] },
      { name: "Todos", extensions: ["*"] },
    ],
    // Varios a la vez: cada archivo queda como una tabla y así se pueden
    // cruzar con JOIN, que es la diferencia entre esto y abrir la planilla.
    properties: ["openFile", "multiSelections"],
  });
  return r.canceled ? null : r.filePaths;
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
ipcMain.handle("ai:refresh-models", (_e, ai) => engine.refreshModels(ai));

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
