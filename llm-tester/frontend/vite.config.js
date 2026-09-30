import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  preview: { proxy: { '/api': { target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8010', changeOrigin: true } } },
  server: { port: 3000, proxy: { '/api': { target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8010', changeOrigin: true } } },
})
