/* © 2026 Martín Viera. Todos los derechos reservados. */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "dist" },
});
