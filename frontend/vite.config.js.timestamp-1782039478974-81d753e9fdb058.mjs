// vite.config.js
import { defineConfig } from "file:///D:/BikeMaster/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/BikeMaster/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import { VitePWA } from "file:///D:/BikeMaster/frontend/node_modules/vite-plugin-pwa/dist/index.js";
var vite_config_default = defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: "prompt",
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
        enabled: true,
        type: "module",
      },
      injectRegister: "script",
      workbox: {
        runtimeCaching: [
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
export { vite_config_default as default };
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxCaWtlTWFzdGVyXFxcXGZyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJEOlxcXFxCaWtlTWFzdGVyXFxcXGZyb250ZW5kXFxcXHZpdGUuY29uZmlnLmpzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9EOi9CaWtlTWFzdGVyL2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcclxuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXHJcbmltcG9ydCB7IFZpdGVQV0EgfSBmcm9tICd2aXRlLXBsdWdpbi1wd2EnXHJcblxyXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xyXG4gIHBsdWdpbnM6IFtcclxuICAgIHZ1ZSgpLFxyXG4gICAgVml0ZVBXQSh7XHJcbiAgICAgIHJlZ2lzdGVyVHlwZTogJ3Byb21wdCcsXHJcbiAgICAgIGluY2x1ZGVBc3NldHM6IFsnZmF2aWNvbi5zdmcnLCAnYXBwbGUtdG91Y2gtaWNvbi5wbmcnLCAncHdhLTE5MngxOTIucG5nJywgJ3B3YS01MTJ4NTEyLnBuZyddLFxyXG4gICAgICBzdHJhdGVnaWVzOiAnaW5qZWN0TWFuaWZlc3QnLFxyXG4gICAgICBzcmNEaXI6ICdzcmMnLFxyXG4gICAgICBmaWxlbmFtZTogJ3N3LmpzJyxcclxuICAgICAgaW5qZWN0TWFuaWZlc3Q6IHtcclxuICAgICAgICBzd0Rlc3Q6ICdzdy5qcycsXHJcbiAgICAgICAgaW5qZWN0aW9uUG9pbnQ6IG51bGwsXHJcbiAgICAgIH0sXHJcbiAgICAgIG1hbmlmZXN0OiB7XHJcbiAgICAgICAgbmFtZTogJ0Jpa2VNYXN0ZXInLFxyXG4gICAgICAgIHNob3J0X25hbWU6ICdCaWtlTWFzdGVyJyxcclxuICAgICAgICBkZXNjcmlwdGlvbjogJ0FkdmFuY2VkIGN5Y2xpbmcgYW5hbHl0aWNzIGFuZCBBSSBjb2FjaGluZycsXHJcbiAgICAgICAgdGhlbWVfY29sb3I6ICcjMTgxYTFiJyxcclxuICAgICAgICBiYWNrZ3JvdW5kX2NvbG9yOiAnI2ZmZmZmZicsXHJcbiAgICAgICAgZGlzcGxheTogJ3N0YW5kYWxvbmUnLFxyXG4gICAgICAgIGljb25zOiBbXHJcbiAgICAgICAgICB7IHNyYzogJ3B3YS0xOTJ4MTkyLnBuZycsIHNpemVzOiAnMTkyeDE5MicsIHR5cGU6ICdpbWFnZS9wbmcnIH0sXHJcbiAgICAgICAgICB7IHNyYzogJ3B3YS01MTJ4NTEyLnBuZycsIHNpemVzOiAnNTEyeDUxMicsIHR5cGU6ICdpbWFnZS9wbmcnIH0sXHJcbiAgICAgICAgXSxcclxuICAgICAgfSxcclxuICAgICAgZGV2T3B0aW9uczoge1xyXG4gICAgICAgIGVuYWJsZWQ6IHRydWUsXHJcbiAgICAgICAgdHlwZTogJ21vZHVsZScsXHJcbiAgICAgIH0sXHJcbiAgICAgIGluamVjdFJlZ2lzdGVyOiAnc2NyaXB0JyxcclxuICAgICAgd29ya2JveDoge1xyXG4gICAgICAgIHJ1bnRpbWVDYWNoaW5nOiBbXHJcbiAgICAgICAgICB7XHJcbiAgICAgICAgICAgIHVybFBhdHRlcm46ICh7IHVybCB9KSA9PiB1cmwucGF0aG5hbWUuc3RhcnRzV2l0aCgnL2FwaS8nKSxcclxuICAgICAgICAgICAgaGFuZGxlcjogJ05ldHdvcmtGaXJzdCcsXHJcbiAgICAgICAgICAgIG9wdGlvbnM6IHtcclxuICAgICAgICAgICAgICBjYWNoZU5hbWU6ICdiaWtlbWFzdGVyLWFwaScsXHJcbiAgICAgICAgICAgICAgZXhwaXJhdGlvbjogeyBtYXhFbnRyaWVzOiAxMDAsIG1heEFnZVNlY29uZHM6IDYwIH0sXHJcbiAgICAgICAgICAgIH0sXHJcbiAgICAgICAgICB9LFxyXG4gICAgICAgICAge1xyXG4gICAgICAgICAgICB1cmxQYXR0ZXJuOiAoeyByZXF1ZXN0IH0pID0+IHJlcXVlc3QuZGVzdGluYXRpb24gPT09ICdpbWFnZScsXHJcbiAgICAgICAgICAgIGhhbmRsZXI6ICdDYWNoZUZpcnN0JyxcclxuICAgICAgICAgICAgb3B0aW9uczoge1xyXG4gICAgICAgICAgICAgIGNhY2hlTmFtZTogJ2Jpa2VtYXN0ZXItaW1hZ2VzJyxcclxuICAgICAgICAgICAgICBleHBpcmF0aW9uOiB7IG1heEVudHJpZXM6IDYwLCBtYXhBZ2VTZWNvbmRzOiAzMCAqIDI0ICogNjAgKiA2MCB9LFxyXG4gICAgICAgICAgICB9LFxyXG4gICAgICAgICAgfSxcclxuICAgICAgICBdLFxyXG4gICAgICB9LFxyXG4gICAgfSksXHJcbiAgXSxcclxuICBidWlsZDoge1xyXG4gICAgcm9sbHVwT3B0aW9uczoge1xyXG4gICAgICBvdXRwdXQ6IHtcclxuICAgICAgICBtYW51YWxDaHVua3M6IHtcclxuICAgICAgICAgICd2ZW5kb3InOiBbJ3Z1ZScsICd2dWUtcm91dGVyJywgJ3BpbmlhJ10sXHJcbiAgICAgICAgICAnY2hhcnRzJzogWydjaGFydC5qcyddLFxyXG4gICAgICAgICAgJ21hcHMnOiBbJ2xlYWZsZXQnLCAnbGVhZmxldC5oZWF0J10sXHJcbiAgICAgICAgfSxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgfSxcclxuICBzZXJ2ZXI6IHtcclxuICAgIGhvc3Q6ICcwLjAuMC4wJyxcclxuICAgIHBvcnQ6IDUxNzMsXHJcbiAgICBwcm94eToge1xyXG4gICAgICAnL2FwaSc6ICdodHRwOi8vbG9jYWxob3N0OjgwMDAnLFxyXG4gICAgICAnL3N0YXRpYyc6ICdodHRwOi8vbG9jYWxob3N0OjgwMDAnLFxyXG4gICAgICAnL2Fzc2V0cyc6ICdodHRwOi8vbG9jYWxob3N0OjgwMDAnLFxyXG4gICAgfSxcclxuICB9LFxyXG4gIHByZXZpZXc6IHtcclxuICAgIHByb3h5OiB7fSxcclxuICB9LFxyXG59KVxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUEwUCxTQUFTLG9CQUFvQjtBQUN2UixPQUFPLFNBQVM7QUFDaEIsU0FBUyxlQUFlO0FBRXhCLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVM7QUFBQSxJQUNQLElBQUk7QUFBQSxJQUNKLFFBQVE7QUFBQSxNQUNOLGNBQWM7QUFBQSxNQUNkLGVBQWUsQ0FBQyxlQUFlLHdCQUF3QixtQkFBbUIsaUJBQWlCO0FBQUEsTUFDM0YsWUFBWTtBQUFBLE1BQ1osUUFBUTtBQUFBLE1BQ1IsVUFBVTtBQUFBLE1BQ1YsZ0JBQWdCO0FBQUEsUUFDZCxRQUFRO0FBQUEsUUFDUixnQkFBZ0I7QUFBQSxNQUNsQjtBQUFBLE1BQ0EsVUFBVTtBQUFBLFFBQ1IsTUFBTTtBQUFBLFFBQ04sWUFBWTtBQUFBLFFBQ1osYUFBYTtBQUFBLFFBQ2IsYUFBYTtBQUFBLFFBQ2Isa0JBQWtCO0FBQUEsUUFDbEIsU0FBUztBQUFBLFFBQ1QsT0FBTztBQUFBLFVBQ0wsRUFBRSxLQUFLLG1CQUFtQixPQUFPLFdBQVcsTUFBTSxZQUFZO0FBQUEsVUFDOUQsRUFBRSxLQUFLLG1CQUFtQixPQUFPLFdBQVcsTUFBTSxZQUFZO0FBQUEsUUFDaEU7QUFBQSxNQUNGO0FBQUEsTUFDQSxZQUFZO0FBQUEsUUFDVixTQUFTO0FBQUEsUUFDVCxNQUFNO0FBQUEsTUFDUjtBQUFBLE1BQ0EsZ0JBQWdCO0FBQUEsTUFDaEIsU0FBUztBQUFBLFFBQ1AsZ0JBQWdCO0FBQUEsVUFDZDtBQUFBLFlBQ0UsWUFBWSxDQUFDLEVBQUUsSUFBSSxNQUFNLElBQUksU0FBUyxXQUFXLE9BQU87QUFBQSxZQUN4RCxTQUFTO0FBQUEsWUFDVCxTQUFTO0FBQUEsY0FDUCxXQUFXO0FBQUEsY0FDWCxZQUFZLEVBQUUsWUFBWSxLQUFLLGVBQWUsR0FBRztBQUFBLFlBQ25EO0FBQUEsVUFDRjtBQUFBLFVBQ0E7QUFBQSxZQUNFLFlBQVksQ0FBQyxFQUFFLFFBQVEsTUFBTSxRQUFRLGdCQUFnQjtBQUFBLFlBQ3JELFNBQVM7QUFBQSxZQUNULFNBQVM7QUFBQSxjQUNQLFdBQVc7QUFBQSxjQUNYLFlBQVksRUFBRSxZQUFZLElBQUksZUFBZSxLQUFLLEtBQUssS0FBSyxHQUFHO0FBQUEsWUFDakU7QUFBQSxVQUNGO0FBQUEsUUFDRjtBQUFBLE1BQ0Y7QUFBQSxJQUNGLENBQUM7QUFBQSxFQUNIO0FBQUEsRUFDQSxPQUFPO0FBQUEsSUFDTCxlQUFlO0FBQUEsTUFDYixRQUFRO0FBQUEsUUFDTixjQUFjO0FBQUEsVUFDWixVQUFVLENBQUMsT0FBTyxjQUFjLE9BQU87QUFBQSxVQUN2QyxVQUFVLENBQUMsVUFBVTtBQUFBLFVBQ3JCLFFBQVEsQ0FBQyxXQUFXLGNBQWM7QUFBQSxRQUNwQztBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsUUFBUTtBQUFBLElBQ04sTUFBTTtBQUFBLElBQ04sTUFBTTtBQUFBLElBQ04sT0FBTztBQUFBLE1BQ0wsUUFBUTtBQUFBLE1BQ1IsV0FBVztBQUFBLE1BQ1gsV0FBVztBQUFBLElBQ2I7QUFBQSxFQUNGO0FBQUEsRUFDQSxTQUFTO0FBQUEsSUFDUCxPQUFPLENBQUM7QUFBQSxFQUNWO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
