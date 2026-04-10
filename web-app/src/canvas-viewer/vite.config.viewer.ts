import { defineConfig } from 'vite';
import * as path from 'path';

// Standalone vite config for the canvas viewer IIFE bundle.
// Usage: npx vite build --config web-app/src/canvas-viewer/vite.config.viewer.ts
//
// Produces viewer.js (minified IIFE) + viewer.css in
// server/pamet/resources/canvas_viewer/.

export default defineConfig({
    build: {
        outDir: path.resolve(__dirname, '../../../server/pamet/resources/canvas_viewer'),
        emptyOutDir: false,
        lib: {
            entry: path.resolve(__dirname, 'viewer.ts'),
            formats: ['iife'],
            name: 'PametViewer',
            fileName: () => 'viewer.js',
        },
        rollupOptions: {
            output: {
                assetFileNames: 'viewer.[ext]',
            },
        },
        minify: 'esbuild',
        cssMinify: true,
        sourcemap: false,
    },
});
