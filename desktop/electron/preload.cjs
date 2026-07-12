const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("mvsql", {
  connect: (cfg) => ipcRenderer.invoke("db:connect", cfg),
  pickSqlite: () => ipcRenderer.invoke("db:pick-sqlite"),
  ask: (payload) => ipcRenderer.invoke("query:ask", payload),
  runSql: (sql) => ipcRenderer.invoke("query:run-sql", { sql }),
  storedProcedure: (payload) => ipcRenderer.invoke("query:stored-procedure", payload),
  optimize: (payload) => ipcRenderer.invoke("query:optimize", payload),
  testAI: (ai) => ipcRenderer.invoke("ai:test", ai),
  storeGet: (key) => ipcRenderer.invoke("store:get", key),
  storeSet: (key, value) => ipcRenderer.invoke("store:set", { key, value }),
  saveFile: (payload) => ipcRenderer.invoke("file:save", payload),
});
