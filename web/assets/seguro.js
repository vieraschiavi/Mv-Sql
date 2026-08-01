// seguro.js — MV SQL NLP
// ===================================================================
// Punto único de escape para cualquier dato (usuario, API externa, base
// de datos) que se inserte en el DOM como HTML. Antes cada página
// justificaba con un comentario por qué SU innerHTML era seguro; acá
// queda una función auditada y con test de regresión propio
// (web/tests/seguro.test.js), en vez de confiar en que el comentario
// siga siendo cierto después del próximo cambio que alguien haga ahí.
//
// Si el destino es textContent/createTextNode no hace falta pasar por
// acá: esas APIs del navegador ya tratan el valor como texto plano,
// nunca como HTML, así que escaparlo antes lo rompería (quedaría
// "&lt;" literal en pantalla). escapeHTML() es para cuando de verdad
// hay que armar un string de HTML a mano.
//
// ── Clasificación de los innerHTML del repo ────────────────────────
// Cada uso de innerHTML en código propio lleva un comentario con una
// de estas cinco etiquetas, y web/tests/innerhtml-inventario.test.js
// falla si aparece uno nuevo sin clasificar:
//
//   [A] VACIADO      innerHTML = "" literal. No puede introducir markup.
//   [B] LITERAL      interpola solo cadenas del diccionario I18N de este
//                    repo (llevan <b>/<br> a propósito). Sin dato externo.
//   [C] LECTURA      lee innerHTML, no escribe.
//   [D] ESCAPADO     lleva dato externo, pasado por escapeHTML() primero.
//   [E] CRUDO        dato externo sin escapar. Tiene que ser SIEMPRE cero.
// ===================================================================
(function (global) {
  "use strict";

  var ENTIDADES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

  function escapeHTML(valor) {
    return String(valor == null ? "" : valor).replace(/[&<>"']/g, function (c) {
      return ENTIDADES[c];
    });
  }

  // Wrapper explícito para el caso textContent: mismo resultado que
  // hacerlo a mano, pero da un único lugar para grep-ear y testear
  // "así es como esta app pone datos dinámicos en el DOM".
  function textoSeguro(elemento, valor) {
    if (elemento) elemento.textContent = valor == null ? "" : String(valor);
    return elemento;
  }

  var api = { escapeHTML: escapeHTML, textoSeguro: textoSeguro };

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (global) global.MvSqlSeguro = api;
})(typeof window !== "undefined" ? window : (typeof global !== "undefined" ? global : this));
