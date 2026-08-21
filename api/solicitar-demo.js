/* © 2026 Martín Viera. Todos los derechos reservados. */

// Puente hacia web/api/solicitar-demo.js
//
// El sitio vive en web/, pero el proyecto de Vercel publica desde la raíz del
// repositorio: sin este archivo la ruta /api/solicitar-demo no existe y
// devuelve 404. Acá no va lógica — la implementación real está en
// web/api/solicitar-demo.js, que es también la que cubren los tests.
module.exports = require("../web/api/solicitar-demo.js");
