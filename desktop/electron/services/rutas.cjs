/* © 2026 Martín Viera. Todos los derechos reservados. */

// MV SQL NLP — dónde guarda sus datos la app de escritorio.
//
// Hay dos escenarios de uso y son distintos de verdad:
//
//   INSTALADA (normal, en tu propia máquina): los datos van a la carpeta
//   de usuario de siempre (%APPDATA%\MV SQL NLP). Sobreviven a las
//   actualizaciones y a reinstalar, que es lo que uno quiere.
//
//   PORTABLE (VM o laptop de un cliente): los datos van AL LADO DEL .EXE,
//   en una subcarpeta "datos-mvsql". Cuando terminás el trabajo borrás esa
//   carpeta —o sacás el pendrive— y en esa máquina no queda nada.
//
// La segunda no es una comodidad, es el punto entero de la build portable.
// Hasta acá "portable" solo quería decir que no hacía falta instalador: la
// app igual escribía en %APPDATA% de esa máquina
//
//   · mvsql-store.json  → las CONEXIONES guardadas del cliente
//   · importado.db      → una COPIA de la base que se importó
//   · licencia_mvsql.json → TU licencia
//   · .mvsql_trial.json → la marca de trial
//
// más todo lo que Electron guarda por su cuenta (caché, cookies, Local
// Storage). Trabajando de consultor en la VM de un cliente, eso es dejarle
// sus propios datos y tu licencia en el perfil de una máquina que no es
// tuya, sin que nadie lo haya pedido.
//
// electron-builder define PORTABLE_EXECUTABLE_DIR solo cuando el binario
// se armó con el target "portable", así que la variable ES la señal de en
// cuál de los dos escenarios estamos. No hay que configurar nada.
const path = require("path");

const SUBCARPETA = "datos-mvsql";

/**
 * La carpeta de datos que corresponde al modo en que se está corriendo,
 * o null si es una instalación normal (y entonces manda la de Electron).
 *
 * `env` se inyecta en los tests; por defecto lee el entorno real.
 */
function carpetaPortable(env) {
  const e = env || process.env;
  const dir = e.PORTABLE_EXECUTABLE_DIR;
  if (!dir) return null;                 // instalación normal
  return path.join(dir, SUBCARPETA);
}

/**
 * Deja la carpeta de datos apuntando donde corresponde. Se llama UNA vez,
 * al principio de main.cjs y antes de que la app esté lista: después de
 * ese punto Electron ya abrió archivos en la ruta vieja y moverla deja la
 * mitad de los datos de cada lado.
 *
 * Se cambia el userData de Electron en vez de la ruta de cada módulo a
 * propósito: así se mueve TAMBIÉN lo que guarda Electron solo (caché,
 * cookies, Local Storage), que es la parte que ningún módulo controla y
 * la que de verdad deja rastro en la máquina del cliente.
 *
 * Devuelve la carpeta que quedó configurada, o null si no se tocó nada.
 */
function configurarCarpetaDatos(app, env) {
  const destino = carpetaPortable(env);
  if (!destino) return null;
  try {
    require("fs").mkdirSync(destino, { recursive: true });
    app.setPath("userData", destino);
    return destino;
  } catch {
    // Sin permiso de escritura al lado del .exe (un pendrive de solo
    // lectura, una carpeta bloqueada por política de la empresa) se
    // sigue con la ruta de siempre: mejor que ande dejando rastro a que
    // no abra. El aviso queda en la consola para poder diagnosticarlo.
    console.warn("[mvsql] no se pudo usar la carpeta portable, se usa la de usuario:", destino);
    return null;
  }
}

module.exports = { carpetaPortable, configurarCarpetaDatos, SUBCARPETA };
