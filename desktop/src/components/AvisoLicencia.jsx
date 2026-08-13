/* © 2026 Martín Viera. Todos los derechos reservados. */

import Icono from "./Icono.jsx";
import { avisoTrial } from "../licencia-aviso.js";

/**
 * Barra de estado de la prueba gratuita.
 *
 * Hasta acá el trial existía pero era invisible: el proceso principal lo
 * verificaba y bloqueaba la app al séptimo día, y el cliente no tenía
 * forma de saber cuántos le quedaban. La app abría normal seis días y al
 * séptimo dejaba de abrir, sin aviso previo — la peor manera de pedirle
 * plata a alguien, porque se entera cuando ya no puede trabajar y encima
 * parece que el programa se rompió.
 *
 * Qué avisar lo decide avisoTrial(), que vive aparte y sin JSX para poder
 * verificarse sin bundler. Este componente solo dibuja.
 */
export default function AvisoLicencia({ t, estado }) {
  const aviso = avisoTrial(estado, t);
  if (!aviso) return null;

  return (
    <div className={`aviso-trial${aviso.urgente ? " urgente" : ""}`} role="status">
      <Icono n="reloj" />
      <span>{aviso.texto}</span>
      <a href={aviso.url} target="_blank" rel="noreferrer">{aviso.cta}</a>
    </div>
  );
}
