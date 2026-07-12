// vite.config.js
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const frontendPort = Number(env.VITE_FRONTEND_DEV_PORT || env.FRONTEND_PORT || 3000);
  const backendHost = env.VITE_BACKEND_HOST || process.env.VITE_BACKEND_HOST || "127.0.0.1";
  const backendPort = env.VITE_BACKEND_PORT || process.env.VITE_BACKEND_PORT || env.BACKEND_PORT || process.env.BACKEND_PORT || 8001;
  const backendUrl =
    env.VITE_BACKEND_URL || process.env.VITE_BACKEND_URL || `http://${backendHost}:${backendPort}`;

  return {
    plugins: [react()],
    server: {
      port: frontendPort,
      host: true,
      strictPort: true,
      hmr: {
        clientPort: frontendPort,
      },
      proxy: {
        "^/(api|auth|authoring|categories|users|dashboard|enrol|uploads|tasks|pal|notifications|settings|admin|signup|courses|health|moodle|public)": {
          target: backendUrl,
          changeOrigin: true,
          bypass: (req) => {
            if (req.headers.accept && req.headers.accept.includes("text/html")) {
              return "/index.html";
            }
          },
        },
      },
    },
  };
});
