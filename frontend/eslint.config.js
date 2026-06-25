{
  "extends": ["eslint:recommended", "plugin:vue/vue3-recommended", "prettier"],
  "plugins": ["vue"],
  "env": {
    "browser": true,
    "node": true,
    "vitest": true
  },
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module"
  },
  "rules": {
    "vue/multi-word-component-names": ["error", { "ignores": ["ToastContainer"] }]
  }
}