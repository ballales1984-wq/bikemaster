import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { VitePWA } from "vite-plugin-pwa";

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, normalize } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Middleware che serve i file .wasm grezzi (es. public/sqlite3/sqlite3.wasm)
// con il MIME corretto, bypassando la pipeline di transform di Vite che
// altrimenti va in hang sulle richieste dirette al .wasm in dev.
function wasmStaticMiddleware() {
  return async (req, res, next) => {
    const url = (req.url || "").split("?")[0];
    if (!url.endsWith(".wasm")) return next();
    const candidate = join(__dirname, "public", normalize(url));
    if (!existsSync(candidate)) return next();
    try {
      const buf = await readFile(candidate);
      res.setHeader("Content-Type", "application/wasm");
      res.setHeader("Cross-Origin-Resource-Policy", "same-origin");
      res.setHeader("Cache-Control", "public, max-age=31536000, immutable");
      res.end(buf);
    } catch {
      next();
    }
  };
}

const env =
  (typeof import.meta !== "undefined" && import.meta.env) || {};
const isTauri =
  env.TAURI === "true" ||
  env.TAURI_ENV_PLATFORM === "win32" ||
  env.TAURI_ENV_PLATFORM === "darwin" ||
  env.TAURI_ENV_PLATFORM === "linux";
const isDev = process.env.NODE_ENV !== "production";
console.log("[vite-config] NODE_ENV:", process.env.NODE_ENV, "isDev:", isDev, "isTauri:", isTauri);

export default defineConfig({
  base: isTauri ? "./" : "/",
  resolve: {
    alias: {
      "leaflet$": "leaflet/dist/leaflet-src.esm.js",
    },
  },
  plugins: [
    vue(),
      !isTauri && !isDev &&
      VitePWA({
        registerType: "autoUpdate",
        workbox: {
          skipWaiting: true,
          clientsClaim: true,
          runtimeCaching: [
            {
              urlPattern: ({ url }) => url.pathname.startsWith("/api/v1/rides"),
              handler: "StaleWhileRevalidate",
              options: {
                cacheName: "bikemaster-rides",
                expiration: { maxEntries: 50, maxAgeSeconds: 30 },
              },
            },
            {
              urlPattern: ({ url }) =>
                url.pathname.startsWith("/api/") &&
                (url.pathname.includes("/auth/") ||
                  url.pathname.includes("/auth")),
              handler: "NetworkOnly",
              options: {
                cacheName: "bikemaster-api",
              },
            },
            {
              urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
              handler: "NetworkOnly",
              options: {
                cacheName: "bikemaster-api",
              },
            },
            {
              urlPattern: ({ request }) => request.destination === "image",
              handler: "CacheFirst",
              options: {
                cacheName: "bikemaster-images",
                expiration: { maxEntries: 500, maxAgeSeconds: 2592000 },
              },
            },
            {
              urlPattern: ({ url }) =>
                url.pathname === "/favicon.svg" ||
                url.pathname.startsWith("/manifest"),
              handler: "CacheFirst",
              options: {
                cacheName: "bikemaster-static",
                expiration: { maxEntries: 10, maxAgeSeconds: 86400 },
              },
            },
          ],
        },
      }),
  ].filter(Boolean),
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["vue", "vue-router", "pinia"],
          charts: ["chart.js"],
        },
      },
    },
  },
  // @sqlite.org/sqlite-wasm NON deve essere pre-bundlato da esbuild in dev:
  // il suo grafo (wasm embedded) fa deadlockare l'optimizer e il server resta
  // irresponsivo. Escludendolo, Vite lo serve direttamente e `localDb.ts`
  // risolve sqlite3.wasm dalla copia in public/sqlite3/.
  optimizeDeps: {
    exclude: ["@sqlite.org/sqlite-wasm"],
  },
  server: {
    host: "0.0.0.0",
    port: 5177,
    strictPort: true,
    // Necessari per SQLite WASM/OPFS: senza questi header `crossOriginIsolated`
    // è false, SharedArrayBuffer non esiste e l'OPFS async proxy worker non
    // parte (fallback automatico a DB in-memory, vedi localDb.ts).
    headers: {
      "Cross-Origin-Embedder-Policy": "require-corp",
      "Cross-Origin-Opener-Policy": "same-origin",
    },
    proxy: {
      "/api": "http://localhost:8000",
      "/static": "http://localhost:8000",
      "/assets": "http://localhost:8000",
    },
    configureServer: (server) => {
      server.middlewares.use(wasmStaticMiddleware());
    },
  },
  preview: {
    headers: {
      "Cross-Origin-Embedder-Policy": "require-corp",
      "Cross-Origin-Opener-Policy": "same-origin",
    },
    proxy: {},
    configurePreviewServer: (server) => {
      server.middlewares.use(wasmStaticMiddleware());
    },
  },
});
