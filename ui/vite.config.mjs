import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [
    react(),
    {
      name: "phase-development-entry",
      apply: "serve",
      transformIndexHtml: {
        order: "pre",
        handler(html) {
          // Production HTML is also embedded by portable_demo.py.
          return html.replace('href="/ui/style.css"', 'href="/style.css"')
            .replace('<script defer src="/plot.js">', '<script src="/plot.js">')
            .replace('<script defer src="/ui/app.js">', '<script type="module" src="/src/main.jsx">');
        },
      },
    },
  ],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": backend, "/plot.js": backend },
  },
});
