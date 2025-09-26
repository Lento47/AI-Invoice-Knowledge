import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/portal/',
  build: {
    outDir: '../../src/api/static/console',
    emptyOutDir: true
  },
  server: {
    port: 5173,
    host: '0.0.0.0'
  }
});
