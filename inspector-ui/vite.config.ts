import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@mcp-server': path.resolve(__dirname, '../mcp-server/src')
    }
  },
  optimizeDeps: {
    include: [
      'react-markdown',
      'remark-gfm',
      'prismjs',
      'react-resizable-panels'
    ]
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3002',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
});
