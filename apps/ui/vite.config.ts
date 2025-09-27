import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(currentDir, '..', '..', 'src/api/static/console');

export default defineConfig({
  plugins: [react()],
  base: '/portal/',
  build: {
    outDir,
    emptyOutDir: true,
    sourcemap: true
  },
  server: {
    port: 5173,
    host: '0.0.0.0'
  }
});
