/* © 2026 Martín Viera. Todos los derechos reservados. */

// Puente hacia web/api/estado.js
//
// El sitio vive en web/, pero el proyecto de Vercel publica desde la raíz del
// repositorio: sin este archivo la ruta /api/estado no existe y devuelve 404.
// Acá no va lógica — la implementación real está en web/api/estado.js, que es
// también la que cubren los tests.
module.exports = require("../web/api/estado.js");
