/* © 2026 Martín Viera. Todos los derechos reservados. */

// Configuración de ESLint (flat config, ESLint 9).
// ===================================================================
// El repo no tenía linter. Este arranca deliberadamente austero: reglas
// que atrapan bugs de verdad (variables sin declarar, promesas mal
// usadas, código inalcanzable), no de estilo. Un linter que grita por
// comillas o punto y coma se termina apagando, y entonces no atrapa nada.
//
// Los globals salen del paquete `globals` y no de una lista escrita a
// mano: la lista a mano se olvida de TextEncoder, IntersectionObserver,
// requestAnimationFrame... y esos falsos positivos son exactamente lo
// que hace que un linter pierda credibilidad.
//
//     npm run lint
// ===================================================================

import js from "@eslint/js";
import globals from "globals";

export default [
  {
    ignores: [
      "node_modules/**",
      "**/node_modules/**",
      "desktop/dist/**",
      "desktop/release/**",
      "web/downloads/**",
      "app-python/**",   // Python: no lo cubre ESLint
    ],
  },

  // Funciones serverless, tests de Node y scripts CommonJS
  {
    files: ["web/api/**/*.js", "api/**/*.js", "web/tests/**/*.js",
            "tools/**/*.js", "desktop/electron/**/*.cjs"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "commonjs",
      globals: { ...globals.node },
    },
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": ["error", {
        argsIgnorePattern: "^_",
        caughtErrorsIgnorePattern: "^_",
      }],
    },
  },

  // Herramientas del repo en ES modules
  {
    files: ["tools/**/*.mjs"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      globals: { ...globals.node, ...globals.browser },
    },
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": ["error", {
        argsIgnorePattern: "^_",
        caughtErrorsIgnorePattern: "^_",
      }],
    },
  },

  // Frontend de la landing y del panel del dueño
  {
    files: ["web/assets/**/*.js"],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "script",
      globals: {
        ...globals.browser,
        // Definido en assets/i18n.js, que se carga aparte.
        I18N: "readonly",
        // Utilidad de escape compartida — assets/seguro.js, cargado en un
        // <script> aparte antes de este archivo en cada página que lo usa.
        MvSqlSeguro: "readonly",
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": ["error", {
        argsIgnorePattern: "^_",
        caughtErrorsIgnorePattern: "^_",
      }],
    },
  },

  // seguro.js: UMD deliberado (script de navegador Y módulo CommonJS para
  // que web/tests/seguro.test.js lo pueda requerir sin bundler). Va DESPUÉS
  // del bloque general de arriba para que sus globals lo pisen solo a él.
  {
    files: ["web/assets/seguro.js"],
    languageOptions: {
      globals: { ...globals.node },
    },
  },

  // React del escritorio
  {
    files: ["desktop/src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...globals.browser },
    },
    rules: {
      ...js.configs.recommended.rules,
      // JSX usa React y los componentes sin "referenciarlos" a ojos del
      // linter base; sin el plugin de React eso da falsos positivos.
      "no-unused-vars": ["error", {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^(React|[A-Z])",
      }],
    },
  },
];
