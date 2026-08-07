// MV SQL NLP — Excel y CSV como si fueran una base
// ==================================================================
// Se importa el archivo a una base SQLite local y despues se consulta
// esa base. La alternativa era cargar el archivo en memoria y armar un
// motor de consultas propio, y se descarto por dos razones:
//
//   1. Tamano. Cargar en memoria pone un techo igual a la RAM de la
//      maquina del cliente. Un CSV se lee de a pedazos y se inserta en
//      disco, asi que un archivo mas grande que la RAM entra igual.
//   2. Un motor propio seria SQL de mentira: habria que reimplementar
//      JOIN, GROUP BY, ventanas... y cada hueco aparece como "esa
//      consulta no anda" delante del cliente. SQLite ya es SQL.
//
// Ademas, al quedar como una base normal, todo lo que ya existe sigue
// funcionando sin tocarse: la extraccion de catalogo, la validacion
// anti-alucinacion contra el esquema real, y la barrera de solo-lectura.
// La base importada se abre readonly como cualquier otra.
//
// Limite honesto sobre "sin limite de tamano": vale para CSV/TXT, que se
// leen en streaming. Un .xlsx es un zip de XML y la libreria que lo lee
// necesita el libro entero en memoria, asi que ahi el techo lo pone el
// archivo, no nosotros. Por eso, cuando un Excel es enorme, el error lo
// dice y sugiere exportarlo a CSV en vez de fallar sin explicacion.
// ==================================================================
const fs = require("fs");
const path = require("path");
const { StringDecoder } = require("string_decoder");

const LOTE = 2000;        // filas por INSERT: mas grande no acelera y come RAM
const MUESTRA_TIPOS = 500; // filas que se miran para deducir el tipo de columna

// ── nombres SQL seguros ─────────────────────────────────────────
// Los encabezados de un Excel real traen acentos, espacios, parentesis,
// simbolos de moneda y a veces estan repetidos. Si eso llega crudo al
// CREATE TABLE, la consulta que escriba la IA no va a poder nombrarlos.
function identificador(nombre, usados, porDefecto) {
  let n = String(nombre ?? "").trim()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")  // saca acentos
    .replace(/[^A-Za-z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (!n || /^\d/.test(n)) n = porDefecto + (n ? "_" + n : "");
  n = n.slice(0, 60);
  let final = n, i = 2;
  while (usados.has(final.toLowerCase())) final = `${n}_${i++}`;
  usados.add(final.toLowerCase());
  return final;
}

// ── tipos ───────────────────────────────────────────────────────
const RE_ENTERO = /^-?\d{1,18}$/;
const RE_REAL = /^-?\d{1,15}([.,]\d+)?$/;
const RE_FECHA = /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})([T ].*)?$/;
const RE_FECHA_LATAM = /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/;

function normalizarFecha(v) {
  let m = RE_FECHA.exec(v);
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}${m[4] ? m[4].replace(" ", "T") : ""}`;
  m = RE_FECHA_LATAM.exec(v);
  // dd/mm/yyyy: en es/pt el dia va primero. Si el primer numero pasa de
  // 12 no hay ambiguedad; si no, se asume dia/mes, que es lo que usa el
  // usuario de este producto.
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return null;
}

function deducirTipos(filas, cantColumnas) {
  const tipos = [];
  for (let c = 0; c < cantColumnas; c++) {
    let ent = 0, real = 0, fecha = 0, vistos = 0;
    for (const f of filas) {
      const v = f[c];
      if (v === null || v === undefined || v === "") continue;
      vistos++;
      const s = String(v).trim();
      if (RE_ENTERO.test(s)) { ent++; real++; }
      else if (RE_REAL.test(s)) real++;
      else if (normalizarFecha(s)) fecha++;
    }
    // Todo vacio => TEXT: inventar un tipo numerico para una columna sin
    // datos hace que despues falle el primer valor de texto que llegue.
    if (!vistos) tipos.push("TEXT");
    else if (ent === vistos) tipos.push("INTEGER");
    else if (real === vistos) tipos.push("REAL");
    else if (fecha === vistos) tipos.push("DATE");
    else tipos.push("TEXT");
  }
  return tipos;
}

function convertir(v, tipo) {
  if (v === null || v === undefined || v === "") return null;
  const s = String(v).trim();
  if (tipo === "INTEGER") { const n = parseInt(s, 10); return Number.isNaN(n) ? s : n; }
  if (tipo === "REAL") { const n = parseFloat(s.replace(",", ".")); return Number.isNaN(n) ? s : n; }
  if (tipo === "DATE") return normalizarFecha(s) || s;
  return s;
}

// ── CSV en streaming ────────────────────────────────────────────
// Parser propio y no una libreria porque hace falta que consuma el
// archivo de a pedazos: es lo unico que permite un CSV mas grande que la
// RAM. Cubre comillas, comillas escapadas ("") y saltos de linea dentro
// de un campo entrecomillado, que es donde fallan los splits ingenuos.
function sniffDelimitador(cabecera) {
  const cands = [",", ";", "\t", "|"];
  let mejor = ",", max = -1;
  for (const d of cands) {
    // Cuenta fuera de comillas para no contar los separadores del texto.
    let n = 0, dentro = false;
    for (let i = 0; i < cabecera.length; i++) {
      const ch = cabecera[i];
      if (ch === '"') dentro = !dentro;
      else if (ch === d && !dentro) n++;
    }
    if (n > max) { max = n; mejor = d; }
  }
  return mejor;
}

function crearParser(delim, alFila) {
  let campo = "", fila = [], dentro = false, prevComilla = false;
  return {
    push(txt) {
      for (let i = 0; i < txt.length; i++) {
        const ch = txt[i];
        if (dentro) {
          if (prevComilla) {
            prevComilla = false;
            if (ch === '"') { campo += '"'; continue; }  // "" escapada
            dentro = false;                                // cierre de comillas
          } else if (ch === '"') { prevComilla = true; continue; }
          else { campo += ch; continue; }
        }
        if (ch === '"' && campo === "") { dentro = true; continue; }
        if (ch === delim) { fila.push(campo); campo = ""; continue; }
        if (ch === "\n") { fila.push(campo); campo = ""; alFila(fila); fila = []; continue; }
        if (ch === "\r") continue;
        campo += ch;
      }
    },
    fin() {
      if (campo !== "" || fila.length) { fila.push(campo); alFila(fila); }
    },
  };
}

async function importarCsv(conn, archivo, tabla, avisar) {
  const fd = fs.openSync(archivo, "r");
  const buf = Buffer.alloc(1 << 20);   // 1 MB por lectura
  let primera = true, delim = ",", cabecera = null, tipos = null;
  let muestra = [], pendientes = [], total = 0, insertar = null;

  const usados = new Set();
  const crearTabla = () => {
    const cols = cabecera.map((h, i) => `"${identificador(h, usados, "col_" + (i + 1))}" ${tipos[i] === "DATE" ? "TEXT" : tipos[i]}`);
    conn.exec(`CREATE TABLE "${tabla}" (${cols.join(", ")})`);
    insertar = conn.prepare(
      `INSERT INTO "${tabla}" VALUES (${cabecera.map(() => "?").join(", ")})`);
  };

  const volcar = (filas) => {
    const tx = conn.transaction((fs_) => {
      for (const f of fs_) {
        const vals = cabecera.map((_, i) => convertir(f[i], tipos[i]));
        insertar.run(vals);
      }
    });
    tx(filas);
    total += filas.length;
    if (avisar) avisar(total);
  };

  const alFila = (f) => {
    if (primera) {
      primera = false;
      cabecera = f;
      return;
    }
    if (!tipos) {
      muestra.push(f);
      if (muestra.length >= MUESTRA_TIPOS) {
        tipos = deducirTipos(muestra, cabecera.length);
        crearTabla();
        volcar(muestra);
        muestra = [];
      }
      return;
    }
    pendientes.push(f);
    if (pendientes.length >= LOTE) { volcar(pendientes); pendientes = []; }
  };

  // El parser se arma recien cuando se sabe el delimitador, que sale de
  // la primera linea: crearlo antes lo dejaria fijado en la coma, y un
  // CSV exportado por Excel en es/pt viene con punto y coma.
  // StringDecoder y no buf.toString(): un chunk corta en un byte
  // cualquiera, y si cae en el medio de un caracter multibyte (cualquier
  // acento, una ñ) lo parte en dos y lo corrompe. El decoder se guarda
  // los bytes sueltos hasta que llega el resto.
  const decoder = new StringDecoder("utf8");
  let parser = null, leidos;
  try {
    while ((leidos = fs.readSync(fd, buf, 0, buf.length, null)) > 0) {
      let txt = decoder.write(buf.subarray(0, leidos));
      if (!txt) continue;
      if (!parser) {
        if (txt.charCodeAt(0) === 0xfeff) txt = txt.slice(1);   // BOM de Excel
        const finLinea = txt.indexOf("\n");
        delim = sniffDelimitador(finLinea > 0 ? txt.slice(0, finLinea) : txt);
        parser = crearParser(delim, alFila);
      }
      parser.push(txt);
    }
    const cola = decoder.end();
    if (cola && parser) parser.push(cola);
  } finally {
    fs.closeSync(fd);
  }
  if (parser) parser.fin();

  // Archivo con menos filas que la muestra: los tipos se deducen recien
  // aca, con lo que haya.
  if (!tipos && cabecera) {
    tipos = deducirTipos(muestra, cabecera.length);
    crearTabla();
    volcar(muestra);
    muestra = [];
  }
  if (pendientes.length) volcar(pendientes);
  if (!cabecera) throw new Error(`El archivo ${path.basename(archivo)} está vacío.`);
  return total;
}

// ── Excel ───────────────────────────────────────────────────────
async function importarExcel(conn, archivo, prefijo, usadosTabla) {
  let XLSX;
  try {
    XLSX = require("xlsx");
  } catch {
    throw new Error("El lector de Excel no está disponible en este build. Exportá el archivo a CSV.");
  }

  let libro;
  try {
    libro = XLSX.readFile(archivo, { cellDates: true, dense: true });
  } catch (e) {
    if (/memory|heap|Array buffer allocation/i.test(e.message)) {
      throw new Error(
        `El Excel ${path.basename(archivo)} es demasiado grande para abrirlo entero ` +
        `(un .xlsx hay que descomprimirlo completo en memoria). Exportalo a CSV y ` +
        `subilo así: el CSV se lee de a pedazos y no tiene ese límite.`);
    }
    throw e;
  }

  const resultado = [];
  for (const hoja of libro.SheetNames) {
    const filas = XLSX.utils.sheet_to_json(libro.Sheets[hoja], { header: 1, raw: false, defval: "" });
    if (!filas.length) continue;
    const cabecera = filas[0];
    const cuerpo = filas.slice(1);
    if (!cabecera.length) continue;

    // Una hoja por tabla. Si el libro tiene una sola, se usa el nombre
    // del archivo: "Hoja1" no le dice nada a la IA ni al usuario.
    const base = libro.SheetNames.length === 1 ? prefijo : `${prefijo}_${hoja}`;
    const tabla = identificador(base, usadosTabla, "tabla");

    const tipos = deducirTipos(cuerpo.slice(0, MUESTRA_TIPOS), cabecera.length);
    const usadosCol = new Set();
    const cols = cabecera.map((h, i) =>
      `"${identificador(h, usadosCol, "col_" + (i + 1))}" ${tipos[i] === "DATE" ? "TEXT" : tipos[i]}`);
    conn.exec(`CREATE TABLE "${tabla}" (${cols.join(", ")})`);

    const insertar = conn.prepare(
      `INSERT INTO "${tabla}" VALUES (${cabecera.map(() => "?").join(", ")})`);
    const tx = conn.transaction((fs_) => {
      for (const f of fs_) insertar.run(cabecera.map((_, i) => convertir(f[i], tipos[i])));
    });
    for (let i = 0; i < cuerpo.length; i += LOTE) tx(cuerpo.slice(i, i + LOTE));

    resultado.push({ tabla, filas: cuerpo.length });
  }
  if (!resultado.length) throw new Error(`El Excel ${path.basename(archivo)} no tiene hojas con datos.`);
  return resultado;
}

/**
 * Importa una lista de archivos a una base SQLite nueva y devuelve su
 * ruta. Cada archivo (o cada hoja de Excel) queda como una tabla, asi
 * que se pueden subir varios y cruzarlos con JOIN.
 */
async function importar(rutas, destino, avisar) {
  const Database = require("better-sqlite3");
  if (fs.existsSync(destino)) fs.unlinkSync(destino);
  fs.mkdirSync(path.dirname(destino), { recursive: true });

  const conn = new Database(destino);
  // La importacion es lo unico que escribe, y sobre una base nuestra —
  // nunca sobre la del cliente. Despues se cierra y se reabre readonly.
  conn.pragma("journal_mode = OFF");
  conn.pragma("synchronous = OFF");

  const usadosTabla = new Set();
  const tablas = [];
  try {
    for (const ruta of rutas) {
      const ext = path.extname(ruta).toLowerCase();
      const prefijo = path.basename(ruta, ext);
      if (ext === ".xlsx" || ext === ".xls" || ext === ".xlsm") {
        for (const r of await importarExcel(conn, ruta, prefijo, usadosTabla)) tablas.push(r);
      } else {
        const tabla = identificador(prefijo, usadosTabla, "tabla");
        const filas = await importarCsv(conn, ruta, tabla,
          avisar ? (n) => avisar({ archivo: path.basename(ruta), filas: n }) : null);
        tablas.push({ tabla, filas });
      }
    }
  } finally {
    conn.close();
  }
  return { destino, tablas };
}

module.exports = { importar, _identificador: identificador, _deducirTipos: deducirTipos, _crearParser: crearParser, _sniffDelimitador: sniffDelimitador, _normalizarFecha: normalizarFecha };
