import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy /api to Flask so the browser sees one origin: the session cookie works
// without CORS configuration. Change the port if Flask runs elsewhere.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
})
