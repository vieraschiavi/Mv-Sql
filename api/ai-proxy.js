// Puente hacia web/api/ai-proxy.js
//
// El sitio vive en web/, pero el proyecto de Vercel publica desde la raíz del
// repositorio: sin este archivo la ruta /api/ai-proxy no existe y devuelve 404.
// Acá no va lógica — la implementación real está en web/api/ai-proxy.js, que es
// también la que cubren los tests.
module.exports = require("../web/api/ai-proxy.js");
