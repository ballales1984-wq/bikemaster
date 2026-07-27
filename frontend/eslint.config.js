import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import pluginPrettier from "eslint-plugin-prettier";
import pluginTs from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import * as vueParser from "vue-eslint-parser";
import prettierConfig from "eslint-config-prettier";

export default [
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "node_modules/@sqlite.org/**",
      ".output/**",
      "coverage/**",
      "tests/**",
      "src-tauri/target/**",
      "test-dist/**",
      "test-pwa.js",
      "android/**",
      "public/sqlite3/**",
      "src/sw.js",
      ".prettierrc.cjs",
      "check-env.mjs",
      "playwright.config.js",
      "vite.config.js",
      "scripts/**",
    ],
  },
  js.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  {
    name: "bikemaster/ts-parser",
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
  },
  {
    name: "bikemaster/ts-only-parser",
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: "latest",
      sourceType: "module",
    },
  },
  {
    name: "bikemaster/rules",
    plugins: {
      prettier: pluginPrettier,
      "@typescript-eslint": pluginTs,
    },
    files: ["**/*.vue", "**/*.ts", "**/*.tsx"],
    rules: {
      "prettier/prettier": "warn",
      "vue/multi-word-component-names": [
        "error",
        { ignores: ["ToastContainer"] },
      ],
      "no-undef": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
    },
  },
  {
    name: "bikemaster/all-globals",
    files: ["**/*"],
    languageOptions: {
      globals: {
        browser: true,
        node: true,
        vitest: true,
        global: "readonly",
        Buffer: "readonly",
        GeolocationPosition: "readonly",
        GeolocationPositionError: "readonly",
        DeviceOrientationEvent: "readonly",
        DeviceMotionEvent: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "off",
    },
  },
  {
    name: "bikemaster/js-unused-vars",
    files: ["**/*.js", "**/*.jsx", "**/*.mjs", "**/*.cjs"],
    rules: {
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
  prettierConfig,
];
