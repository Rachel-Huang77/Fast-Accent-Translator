// tests/frontend/vitest.config.js
// Using npm workspaces to share React between frontend and tests
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const frontendSrc = path.resolve(__dirname, '../../frontend/src')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Alias for importing frontend source code
      '@src': frontendSrc,
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./test/setup.js'],
    include: ['./**/*.{test,spec}.{js,jsx}'],
    css: true,
    // Inline dependencies from frontend/src to enable coverage tracking
    server: {
      deps: {
        inline: [/@src/, /frontend\/src/],
      },
    },
    coverage: {
      // Use v8 provider
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
      // Include source files from frontend/src
      include: [
        '**/frontend/src/**/*.{js,jsx}',
      ],
      exclude: [
        '**/node_modules/**',
        '**/*.test.{js,jsx}',
        '**/*.spec.{js,jsx}',
        '**/*.config.{js,ts}',
        '**/__tests__/**',
        '**/test/**',
        '**/coverage/**',
        '**/dist/**',
      ],
      // Allow external files
      allowExternal: true,
      // Track all files in include, even if not executed
      all: true, 
    },
  },
})

