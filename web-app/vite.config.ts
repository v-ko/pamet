import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import * as path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  root: 'src',
  build: {
    sourcemap: true,
  },
  plugins: [
    react(),
  ],
  server: {
    port: 3000,
  },
  resolve: {
    alias: {
      'fusion': path.resolve(__dirname, '../fusion/js-src/src'),
      '@': path.resolve(__dirname, './src'),
    },
  },
})
