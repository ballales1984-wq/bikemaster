import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import pluginPrettier from "eslint-plugin-prettier";
import tsParser from "@typescript-eslint/parser";
import * as vueParser from "vue-eslint-parser";

export default [
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      ".output/**",
      "coverage/**",
      "tests/**",
    ],
  },
  js.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  {
    name: "bikemaster/ts-parser",
    files: ["**/*.vue", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"],
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
    name: "bikemaster/custom",
    languageOptions: {
      globals: {
        browser: true,
        node: true,
        vitest: true,
      },
    },
  },
  {
    name: "bikemaster/rules",
    plugins: {
      prettier: pluginPrettier,
    },
    rules: {
      "prettier/prettier": "warn",
      "vue/multi-word-component-names": [
        "error",
        { ignores: ["ToastContainer"] },
      ],
    },
  },
];
