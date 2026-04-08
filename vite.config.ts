import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import * as path from 'path';
import * as fs from 'fs';

// https://vitejs.dev/config/
// Support multiple build modes: 'web' (default) and 'desktop'
const buildMode = process.env.BUILD_MODE || 'web';
const isDesktop = buildMode === 'desktop';

// Auto-detect local fusion source for tandem development.
// Falls back to the npm package if the sibling repo isn't present.
const fusionLocalPath = path.resolve(__dirname, '../fusion/js-src/src');
const fusionDev = fs.existsSync(fusionLocalPath);

export default defineConfig({
  root: './web-app/src',
  publicDir: '../public',
  build: {
    outDir: isDesktop ? '../dist-desktop' : '../dist',
    sourcemap: true,
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'web-app/src/index.html'),
    }
  },
  plugins: [
    react(),
  ],
  server: {
    port: 3000,
    // Allow Vite to serve the lib files from the sibling dir
    ...(fusionDev ? { fs: { allow: [path.resolve(__dirname, '..')] } } : {}),
  },
  resolve: {
    alias: {
      ...(fusionDev ? { 'fusion': fusionLocalPath } : {}),
      '@': path.resolve(__dirname, './web-app/src'),
    },
  },
  define: {
    'import.meta.env.BUILD_MODE': JSON.stringify(buildMode),
  }
})
