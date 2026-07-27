// Puente hacia web/api/webhook.js
//
// El sitio vive en web/, pero el proyecto de Vercel publica desde la raíz del
// repositorio: sin este archivo la ruta /api/webhook no existe y devuelve 404.
// Acá no va lógica — la implementación real está en web/api/webhook.js, que es
// también la que cubren los tests.
module.exports = require("../web/api/webhook.js");
