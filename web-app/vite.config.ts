import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
  },
  resolve: {
    // preserveSymlinks: true,
    alias: {
      'pyfusion': path.resolve(__dirname,'../fusion/js-src/src'),
    },
  },
})
