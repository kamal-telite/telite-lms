// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    target: "es2020",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined;
          }
          if (id.includes("chart.js") || id.includes("react-chartjs-2")) {
            return "vendor-charts";
          }
          if (id.includes("jspdf")) {
            return "vendor-pdf";
          }
          if (id.includes("@dnd-kit")) {
            return "vendor-dnd";
          }
          if (id.includes("react-router") || id.includes("react-dom") || id.includes("/react/") || id.includes("zustand")) {
            return "vendor-react";
          }
          if (id.includes("axios")) {
            return "vendor-data";
          }
          if (id.includes("lenis")) {
            return "vendor-lenis";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    port: 3000,
    host: true,
    strictPort: true,
    hmr: {
      clientPort: 3000,
    },
    proxy: {
      "^/(api|auth|authoring|categories|users|dashboard|enrol|tasks|pal|notifications|settings|admin|signup|courses|health|moodle)": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: (req, res, options) => {
          if (req.headers.accept && req.headers.accept.includes("text/html")) {
            return "/index.html";
          }
        },
      },
    },
  },
});
