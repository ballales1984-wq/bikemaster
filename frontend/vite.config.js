import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: [
        "favicon.svg",
        "apple-touch-icon.png",
        "pwa-192x192.png",
        "pwa-512x512.png",
      ],
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.js",
      injectManifest: {
        swDest: "sw.js",
        injectionPoint: null,
      },
      manifest: {
        name: "BikeMaster",
        short_name: "BikeMaster",
        description: "Advanced cycling analytics and AI coaching",
        theme_color: "#181a1b",
        background_color: "#ffffff",
        display: "standalone",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      devOptions: {
        enabled: false,
        type: "module",
      },
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
            handler: "NetworkFirst",
            options: {
              cacheName: "bikemaster-api",
              expiration: { maxEntries: 10, maxAgeSeconds: 0 },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
            handler: "NetworkFirst",
            options: {
              cacheName: "bikemaster-api",
              expiration: { maxEntries: 100, maxAgeSeconds: 60 },
            },
          },
          {
            urlPattern: ({ request }) => request.destination === "image",
            handler: "CacheFirst",
            options: {
              cacheName: "bikemaster-images",
              expiration: { maxEntries: 60, maxAgeSeconds: 30 * 24 * 60 * 60 },
            },
          },
        ],
      },
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["vue", "vue-router", "pinia"],
          charts: ["chart.js"],
          maps: ["leaflet", "leaflet.heat"],
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/static": "http://localhost:8000",
      "/assets": "http://localhost:8000",
    },
  },
  preview: {
    proxy: {},
  },
});
