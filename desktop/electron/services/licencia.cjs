/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — trial y licencia de la app Electron
// ==================================================================
// Espejo de app-python/licencia.py. Hasta ahora este modulo no existia
// del lado de Electron: la app de escritorio corria sin limite para
// siempre, o sea que el .exe publicado en Releases ERA el producto
// completo, gratis. El trial de 7 dias que vende la web solo se hacia
// cumplir en el producto Python.
//
// Se replica el formato del de Python a proposito, no por comodidad: la
// licencia que emite la web tras el pago (web/api/download.js) es UNA
// sola, y el cliente que compra tiene que poder usarla con cualquiera de
// los dos productos sin que le expliquemos que hay dos formatos.
//
// Donde viven los archivos (y por que no al lado del .exe, como en la
// version Python): un instalador NSIS deja el programa en Archivos de
// programa o en LOCALAPPDATA\Programs, y la app empaquetada corre desde
// un asar de solo lectura. Escribir la marca de trial ahi falla o pide
// permisos de administrador. Por eso van en userData, que es de la
// cuenta del usuario y siempre escribible.
//
// Limite honesto, igual que en el de Python: esto es proteccion del lado
// del cliente. Sin un servidor que la app consulte en cada arranque, un
// usuario tecnico decidido puede borrar la marca y reiniciar el trial.
// Lo que si se detecta es el truco mas comun (adelantar el reloj) y la
// edicion a mano del archivo, que invalida la firma y REINICIA el trial
// en vez de extenderlo.
// ==================================================================
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const TRIAL_DIAS = 7;

// No es una clave secreta: vive en el mismo binario que se quiere
// proteger. Solo evita que editar la fecha a mano "a ojo" alargue el
// trial sin que se note. Tiene que ser IGUAL a la de licencia.py, para
// que una marca escrita por un producto la entienda el otro.
const SAL = "mvsql-nlp-trial-v1";

const MS_POR_DIA = 86400000;

function firma(inicioIso) {
  return crypto.createHash("sha256").update(SAL + inicioIso, "utf8").digest("hex");
}

// Las rutas se resuelven tarde y se pueden inyectar: asi el modulo se
// puede testear en Node pelado, sin levantar Electron.
function rutas(dirs) {
  if (dirs) return dirs;
  const { app } = require("electron");
  return {
    datos: app.getPath("userData"),
    // La licencia del propietario viaja DENTRO de la build owner, en
    // recursos de solo lectura. Ver desktop/electron-builder.yml.
    recursos: process.resourcesPath || app.getAppPath(),
  };
}

function leerJson(ruta) {
  try {
    // Se le saca el BOM antes de parsear. La licencia del propietario la
    // escribe PowerShell en el runner de Windows, y segun la version le
    // antepone un U+FEFF que JSON.parse rechaza. Sin esta linea, ese
    // caracter invisible hace que la licencia se descarte y la build del
    // propietario muestre el trial, sin ningun error que lo explique.
    //
    // Va escrito como escape \uFEFF y no como el caracter literal:
    // puesto tal cual es invisible en el editor y en el diff, y el
    // linter lo marca como espacio irregular, que es lo que es.
    return JSON.parse(fs.readFileSync(ruta, "utf8").replace(/^\uFEFF/, ""));
  } catch {
    return null;
  }
}

function vigente(lic) {
  if (!lic || !lic.vence) return false;
  const vence = new Date(String(lic.vence).replace(" ", "T"));
  return !Number.isNaN(vence.getTime()) && vence.getTime() > Date.now();
}

function leerMarcaTrial(archivo) {
  const data = leerJson(archivo);
  if (!data) return null;
  const inicio = data.inicio || "";
  // Firma que no cierra = archivo tocado a mano. Se descarta, lo que
  // arranca un trial NUEVO. Editar la fecha para estirar el trial deja
  // al usuario peor que antes, que es justamente la idea.
  if (data.firma !== firma(inicio)) return null;
  return inicio;
}

function crearMarcaTrial(archivo) {
  const inicio = new Date().toISOString();
  try {
    fs.mkdirSync(path.dirname(archivo), { recursive: true });
    fs.writeFileSync(archivo, JSON.stringify({ inicio, firma: firma(inicio) }));
  } catch {
    // Sin permiso de escritura la app sigue andando; solo que el trial
    // no persiste entre arranques. Preferimos eso a no abrir.
  }
  return inicio;
}

/**
 * Chequea si la app puede usarse: con licencia paga vigente, con la
 * licencia del propietario, o dentro del trial gratuito.
 *
 * Efecto lateral: crea la marca de trial la primera vez que se llama.
 *
 * Devuelve {permitido, diasRestantes, conLicencia, esPropietario}.
 * diasRestantes es null cuando hay licencia (no aplica trial).
 */
function verificarAcceso(dirs) {
  const { datos, recursos } = rutas(dirs);
  const archivoMarca = path.join(datos, ".mvsql_trial.json");

  // 1) Build del propietario: la licencia viaja adentro del instalador,
  //    asi que abre sin pedir nada. Es lo que hace que la version owner
  //    no necesite clave.
  const licOwner = leerJson(path.join(recursos, "licencia_owner.json"));
  if (vigente(licOwner)) {
    return { permitido: true, diasRestantes: null, conLicencia: true, esPropietario: true };
  }

  // 2) Licencia comprada: el cliente la deja en userData tras pagar.
  const licPaga = leerJson(path.join(datos, "licencia_mvsql.json"));
  if (vigente(licPaga)) {
    return { permitido: true, diasRestantes: null, conLicencia: true, esPropietario: false };
  }

  // 3) Trial.
  let inicioIso = leerMarcaTrial(archivoMarca);
  if (inicioIso === null) inicioIso = crearMarcaTrial(archivoMarca);

  let inicio = new Date(inicioIso).getTime();
  if (Number.isNaN(inicio)) inicio = Date.now();

  const ahora = Date.now();
  if (ahora < inicio) {
    // El reloj se movio para atras respecto del primer arranque. En vez
    // de regalar dias de trial, se corta.
    return { permitido: false, diasRestantes: 0, conLicencia: false, esPropietario: false };
  }

  const transcurridos = Math.floor((ahora - inicio) / MS_POR_DIA);
  const restantes = Math.max(0, TRIAL_DIAS - transcurridos);
  return {
    permitido: restantes > 0,
    diasRestantes: restantes,
    conLicencia: false,
    esPropietario: false,
  };
}

// ── Renovacion automatica de la suscripcion ────────────────────────
//
// Una suscripcion cobra todos los meses; la licencia se emite una sola
// vez. Mientras la licencia dure un año eso solo regala producto al que
// cancela, pero en cuanto la vigencia se acorte al ciclo de cobro —que
// es a donde tiene que ir— el cliente que SI paga se quedaria afuera
// todos los meses si nadie pide la licencia nueva por el.
//
// El endpoint que la emite ya existe (web/api/renovar-licencia.js) y no
// lo llamaba nadie: la mitad del servidor estaba hecha y la del cliente
// no, o sea que la funcion completa no existia.
//
// Regla de oro de todo esto: NUNCA dejar al cliente peor que antes. Si
// no hay red, si el servidor contesta cualquier cosa, si la respuesta
// viene rota — se deja la licencia que ya tenia y la app abre igual. Lo
// unico que puede pasar es que mejore.

/** Dias antes del vencimiento en que se empieza a intentar renovar.
 *  Con margen a proposito: si el intento cae justo el dia del
 *  vencimiento y ese dia la maquina esta sin red, el cliente que paga
 *  pierde el acceso. Varios dias de ventana dan varios arranques. */
const DIAS_ANTES_DE_RENOVAR = 5;

const URL_RENOVAR = "https://mvsqlnlp.com/api/renovar-licencia";

/** Cuanto se espera al servidor. Esto corre ANTES de abrir la ventana:
 *  un servidor colgado no puede traducirse en una app que no arranca. */
const ESPERA_MS = 8000;

function escribirLicencia(datos, destino) {
  // Primero a un temporal y despues rename, que es atomico: si se corta
  // la luz a mitad de la escritura, el cliente conserva la licencia
  // vieja en vez de quedarse con un JSON truncado que no parsea —o sea,
  // sin licencia, justo cuando acaba de pagar.
  const tmp = `${destino}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(datos, null, 2));
  fs.renameSync(tmp, destino);
}

/**
 * Pide una licencia nueva si la actual esta por vencer y el cliente
 * sigue pagando. No lanza nunca: devuelve por que no se hizo.
 *
 * Estados: "sin-licencia" | "sin-token" | "al-dia" | "renovada" |
 *          "sin-red" | "rechazada" | "respuesta-invalida"
 */
async function renovarSiCorresponde(dirs, opciones = {}) {
  const traer = opciones.fetch || globalThis.fetch;
  const ahora = opciones.ahora || Date.now();
  if (typeof traer !== "function") return { estado: "sin-red" };

  const { datos } = rutas(dirs);
  const archivo = path.join(datos, "licencia_mvsql.json");
  const lic = leerJson(archivo);
  if (!lic) return { estado: "sin-licencia" };

  // Las licencias viejas (y las de la build del propietario) no llevan
  // token: sin el no hay con que acreditarse, y esta bien que asi sea —
  // renovar por email dejaria que cualquiera que lo conozca se lleve la
  // licencia ajena.
  if (!lic.token) return { estado: "sin-token" };

  const vence = new Date(String(lic.vence || "").replace(" ", "T")).getTime();
  // Sin fecha legible se intenta igual: una licencia que la app no sabe
  // hasta cuando vale es exactamente una que conviene renovar.
  if (!Number.isNaN(vence) && vence - ahora > DIAS_ANTES_DE_RENOVAR * MS_POR_DIA) {
    return { estado: "al-dia" };
  }

  let resp;
  try {
    resp = await traer(`${URL_RENOVAR}?token=${encodeURIComponent(lic.token)}`, {
      signal: AbortSignal.timeout(ESPERA_MS),
    });
  } catch {
    // Sin red, DNS caido, timeout. La licencia actual queda intacta.
    return { estado: "sin-red" };
  }

  if (!resp || !resp.ok) {
    // 402 (cancelada), 409 (pago unico), 404, 500... En todos los casos
    // se deja lo que hay: si de verdad cancelo, la licencia vence sola
    // y ahi la puerta lo frena. Borrarla aca convertiria un 500 nuestro
    // en un cliente bloqueado.
    return { estado: "rechazada", codigo: resp ? resp.status : 0 };
  }

  let cuerpo;
  try {
    cuerpo = await resp.json();
  } catch {
    return { estado: "respuesta-invalida" };
  }

  const nueva = cuerpo && cuerpo.licencia;
  // No se pisa nada hasta comprobar que lo nuevo sirve. Escribir una
  // licencia sin `vence` la dejaria muerta al instante, y el cliente
  // veria "compra tu licencia" JUSTO despues de renovar bien.
  if (!nueva || !nueva.token || !vigente(nueva)) {
    return { estado: "respuesta-invalida" };
  }

  try {
    escribirLicencia(nueva, archivo);
  } catch {
    return { estado: "respuesta-invalida" };
  }
  return { estado: "renovada", vence: nueva.vence };
}

/** Guarda la licencia que el cliente pega despues de comprar. */
function instalarLicencia(texto, dirs) {
  const { datos } = rutas(dirs);
  let lic;
  try {
    lic = JSON.parse(texto);
  } catch {
    return { ok: false, motivo: "formato" };
  }
  if (!vigente(lic)) return { ok: false, motivo: "vencida" };
  fs.mkdirSync(datos, { recursive: true });
  fs.writeFileSync(path.join(datos, "licencia_mvsql.json"), JSON.stringify(lic, null, 2));
  return { ok: true, vence: lic.vence };
}

module.exports = {
  verificarAcceso,
  instalarLicencia,
  renovarSiCorresponde,
  TRIAL_DIAS,
  DIAS_ANTES_DE_RENOVAR,
  _firma: firma,
};
