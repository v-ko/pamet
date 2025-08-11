import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import * as path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  root: './web-app/src',
  publicDir: '../public',
  build: {
    outDir: '../dist',
    sourcemap: true,
    emptyOutDir: true,
  },
  plugins: [
    react(),
  ],
  server: {
    port: 3000,
  },
  resolve: {
    alias: {
      'fusion': path.resolve(__dirname, './fusion/js-src/src'),
      '@': path.resolve(__dirname, './web-app/src'),
    },
  },
})
