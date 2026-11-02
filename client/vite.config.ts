import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Where the app is served. Deployed it's /tools/list-parser-bot/ on riccardorestagno.com (set by the
// deploy workflow), on the site the tools dashboard deploys; in development it's the root
const base = process.env.VITE_BASE_PATH || '/';

// https://vite.dev/config/
export default defineConfig({
  base,
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: `dist${base}`,
  },
  server: {
    // Next to the other tools' dev servers: spending-insights on 5173, the dashboard on 5174
    port: 5175,
    // The client calls a relative /api, which goes to the API on :8002 (server/main.py)
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
