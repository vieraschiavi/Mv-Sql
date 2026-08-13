/* © 2026 Martín Viera. Todos los derechos reservados. */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("mvsql", {
  connect: (cfg) => ipcRenderer.invoke("db:connect", cfg),
  pickSqlite: () => ipcRenderer.invoke("db:pick-sqlite"),
  pickArchivos: () => ipcRenderer.invoke("db:pick-archivos"),
  ask: (payload) => ipcRenderer.invoke("query:ask", payload),
  runSql: (sql) => ipcRenderer.invoke("query:run-sql", { sql }),
  storedProcedure: (payload) => ipcRenderer.invoke("query:stored-procedure", payload),
  optimize: (payload) => ipcRenderer.invoke("query:optimize", payload),
  testAI: (ai) => ipcRenderer.invoke("ai:test", ai),
  refreshModels: (ai) => ipcRenderer.invoke("ai:refresh-models", ai),
  storeGet: (key) => ipcRenderer.invoke("store:get", key),
  storeSet: (key, value) => ipcRenderer.invoke("store:set", { key, value }),
  saveFile: (payload) => ipcRenderer.invoke("file:save", payload),
  // Solo para mostrar "te quedan N días": la puerta de acceso ya se
  // resolvió en el proceso principal antes de que existiera esta ventana.
  licenciaEstado: () => ipcRenderer.invoke("licencia:estado"),
});
