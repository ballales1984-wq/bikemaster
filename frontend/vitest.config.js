import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue()],
  test: {
    include: ["src/**/*.test.{js,ts}"],
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.js"],
    coverage: {
      all: false,
      include: ["src/**/*.{js,ts,vue}"],
      exclude: [
        "src/test/**",
        "src/**/*.d.ts",
        "**/*.mock.{js,ts}",
        "**/node_modules/**",
        "**/android/**",
        "android/**",
        "**/android/app/src/main/assets/public/assets/**",
        "**/playwright.config.js",
        "public/**",
        "dist/**",
        "coverage/**",
      ],
    },
  },
});
