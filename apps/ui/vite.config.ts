import path from 'node:path';

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const outDir = path.resolve(__dirname, '../..', 'src/api/static/console');

export default defineConfig({
  plugins: [react()],
  base: '/portal/',
  build: {
    outDir,
    emptyOutDir: true
  },
  server: {
    port: 5173,
    host: '0.0.0.0'
  }
});
