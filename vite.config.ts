import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import * as path from 'path';
import * as fs from 'fs';

// https://vitejs.dev/config/
// Support multiple build modes: 'web' (default) and 'desktop'
const buildMode = process.env.BUILD_MODE || 'web';
const isDesktop = buildMode === 'desktop';

// Auto-detect local sivkit source for tandem development.
// Falls back to the npm package if the sibling repo isn't present.
const sivkitLocalPath = path.resolve(__dirname, '../sivkit/typescript/src');
const sivkitDev = fs.existsSync(sivkitLocalPath);

export default defineConfig({
  root: './web-app/src',
  publicDir: '../public',
  build: {
    // 'web' build → web-app/dist (served by the standalone web deployment)
    // 'desktop' build → server/pamet/desktop_app/_web_app_dist so it ships
    // inside the Python wheel and can be served by DesktopServer.
    outDir: isDesktop
      ? path.resolve(__dirname, 'server/pamet/desktop_app/_web_app_dist')
      : '../dist',
    sourcemap: true,
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'web-app/src/index.html'),
    }
  },
  worker: {
    // Module workers (SharedWorker / ServiceWorker constructed via
    // `new URL(..., import.meta.url)`) need ES output to support
    // code-splitting their dep graph.
    format: 'es',
  },
  plugins: [
    react(),
  ],
  server: {
    port: 3010,
    // Allow Vite to serve the lib files from the sibling dir
    ...(sivkitDev ? { fs: { allow: [path.resolve(__dirname, '..')] } } : {}),
  },
  resolve: {
    alias: {
      ...(sivkitDev ? { 'sivkit': sivkitLocalPath } : {}),
      '@': path.resolve(__dirname, './web-app/src'),
    },
  },
  define: {
    'import.meta.env.BUILD_MODE': JSON.stringify(buildMode),
  }
})
