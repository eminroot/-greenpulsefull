import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In production the panel is served from the same origin as the API, so every
// request is relative and there is no CORS. `npm run dev` runs on its own port,
// so proxy the API through to a server running locally (override with
// GREENPULSE_API).
const target = process.env.GREENPULSE_API || 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.PORT) || 5173,
    proxy: {
      '/api': { target, changeOrigin: true, ws: true },
      '/health': { target, changeOrigin: true },
    },
  },
});
