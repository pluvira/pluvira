import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [
    svelte(),
    tailwindcss()
  ],
  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, './src/lib')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8585',
        changeOrigin: true,
        secure: false
      }
    }
  }
});
