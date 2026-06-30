// vitest.config.js
import vue from "file:///D:/BikeMaster/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import { defineConfig } from "file:///D:/BikeMaster/frontend/node_modules/vitest/dist/config.js";
var vitest_config_default = defineConfig({
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
        "coverage/**"
      ]
    }
  }
});
export {
  vitest_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZXN0LmNvbmZpZy5qcyJdLAogICJzb3VyY2VzQ29udGVudCI6IFsiY29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2Rpcm5hbWUgPSBcIkQ6XFxcXEJpa2VNYXN0ZXJcXFxcZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkQ6XFxcXEJpa2VNYXN0ZXJcXFxcZnJvbnRlbmRcXFxcdml0ZXN0LmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovQmlrZU1hc3Rlci9mcm9udGVuZC92aXRlc3QuY29uZmlnLmpzXCI7aW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXG5pbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlc3QvY29uZmlnJ1xuXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbdnVlKCldLFxuICB0ZXN0OiB7XG4gICAgaW5jbHVkZTogWydzcmMvKiovKi50ZXN0Lntqcyx0c30nXSxcbiAgICBlbnZpcm9ubWVudDogJ2pzZG9tJyxcbiAgICBnbG9iYWxzOiB0cnVlLFxuICAgIHNldHVwRmlsZXM6IFsnLi9zcmMvdGVzdC9zZXR1cC5qcyddLFxuICAgIGNvdmVyYWdlOiB7XG4gICAgICBhbGw6IGZhbHNlLFxuICAgICAgaW5jbHVkZTogWydzcmMvKiovKi57anMsdHMsdnVlfSddLFxuICAgICAgZXhjbHVkZTogW1xuICAgICAgICAnc3JjL3Rlc3QvKionLFxuICAgICAgICAnc3JjLyoqLyouZC50cycsXG4gICAgICAgICcqKi8qLm1vY2sue2pzLHRzfScsXG4gICAgICAgICcqKi9ub2RlX21vZHVsZXMvKionLFxuICAgICAgICAnKiovYW5kcm9pZC8qKicsXG4gICAgICAgICdhbmRyb2lkLyoqJyxcbiAgICAgICAgJyoqL2FuZHJvaWQvYXBwL3NyYy9tYWluL2Fzc2V0cy9wdWJsaWMvYXNzZXRzLyoqJyxcbiAgICAgICAgJyoqL3BsYXl3cmlnaHQuY29uZmlnLmpzJyxcbiAgICAgICAgJ3B1YmxpYy8qKicsXG4gICAgICAgICdkaXN0LyoqJyxcbiAgICAgICAgJ2NvdmVyYWdlLyoqJyxcbiAgICAgIF0sXG4gICAgfSxcbiAgfSxcbn0pXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQThQLE9BQU8sU0FBUztBQUM5USxTQUFTLG9CQUFvQjtBQUU3QixJQUFPLHdCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTLENBQUMsSUFBSSxDQUFDO0FBQUEsRUFDZixNQUFNO0FBQUEsSUFDSixTQUFTLENBQUMsdUJBQXVCO0FBQUEsSUFDakMsYUFBYTtBQUFBLElBQ2IsU0FBUztBQUFBLElBQ1QsWUFBWSxDQUFDLHFCQUFxQjtBQUFBLElBQ2xDLFVBQVU7QUFBQSxNQUNSLEtBQUs7QUFBQSxNQUNMLFNBQVMsQ0FBQyxzQkFBc0I7QUFBQSxNQUNoQyxTQUFTO0FBQUEsUUFDUDtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxNQUNGO0FBQUEsSUFDRjtBQUFBLEVBQ0Y7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
