import { defineConfig } from 'vite';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const backendUrl = env.VITE_BACKEND_URL || 'https://ustad-assist-lbxl.vercel.app/
';
  const proxy = {
    '/api': {
      target: backendUrl,
      changeOrigin: true,
    },
  };

  return {
    plugins: [react()],
    server: { host: '127.0.0.1', port: 5173, proxy },
    preview: { host: '127.0.0.1', port: 5173, proxy },
  };
});
