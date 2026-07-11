// MV SQL NLP — persistencia local simple (JSON en userData)
// Guarda: consultas guardadas, conexiones (sin passwords), config de IA e idioma.
const { app } = require("electron");
const fs = require("fs");
const path = require("path");

const FILE = () => path.join(app.getPath("userData"), "mvsql-store.json");

function readAll() {
  try { return JSON.parse(fs.readFileSync(FILE(), "utf8")); }
  catch { return {}; }
}

function get(key) {
  return readAll()[key] ?? null;
}

function set(key, value) {
  const all = readAll();
  all[key] = value;
  fs.mkdirSync(path.dirname(FILE()), { recursive: true });
  fs.writeFileSync(FILE(), JSON.stringify(all, null, 2));
  return true;
}

module.exports = { get, set };
