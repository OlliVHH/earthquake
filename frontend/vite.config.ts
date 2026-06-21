// Human: Vite dev server config — React plugin and API proxy to backend.
// Agent: READS none at runtime; dev server port 5173; proxies /api to localhost:8000.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  // Human: Forward /api to FastAPI during local development.
  // Agent: HTTP proxy target http://localhost:8000; changeOrigin true.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
