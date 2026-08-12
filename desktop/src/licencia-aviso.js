/**
 * Decide QUÉ avisar sobre la prueba gratuita. Sin JSX y sin React a
 * propósito: separar la decisión del dibujo deja la regla verificable
 * sin bundler ni navegador, que es donde se puede equivocar de verdad
 * (contar mal los días, alarmar de más, o avisarle a quien ya pagó).
 *
 * Devuelve null cuando no hay nada que decir, o {urgente, texto, cta}.
 */

/** Últimos días en los que el aviso cambia a tono de advertencia.
 *  Mismo umbral que el producto Python (app.py, bloque _TXT_AVISO): si
 *  los dos productos avisaran en momentos distintos, el mismo cliente
 *  con las dos versiones vería dos promesas diferentes. */
export const DIAS_URGENTE = 2;

export function avisoTrial(estado, t) {
  // El IPC todavía no contestó: renderizar acá dejaría parpadear una
  // barra vacía en cada arranque.
  if (!estado) return null;
  // Quien pagó ya sabe que pagó; una barra permanente sería solo ruido.
  if (estado.conLicencia) return null;
  if (estado.diasRestantes == null) return null;

  const dias = estado.diasRestantes;
  const urgente = dias <= DIAS_URGENTE;
  return {
    urgente,
    texto: urgente ? t.trial_ultimo(dias) : t.trial_dias(dias),
    cta: t.trial_cta,
    url: "https://mvsqlnlp.com/#precios",
  };
}
