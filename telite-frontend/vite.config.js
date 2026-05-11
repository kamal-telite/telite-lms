// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Listen on all local IPs
    strictPort: true,
    hmr: {
      clientPort: 3000,
    },
    proxy: {
      "^/(api|auth|categories|users|dashboard|enrol|tasks|pal|notifications|settings|admin|signup|courses|health|moodle)": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
    },
  },
});
