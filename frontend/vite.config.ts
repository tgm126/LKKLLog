import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Při vývoji přeposílá Vite volání API a administrace na Django (manage.py runserver).
const django = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': django,
      '/admin': django,
      '/static': django,
    },
  },
})
