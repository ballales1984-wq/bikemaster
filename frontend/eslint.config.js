import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginPrettier from 'eslint-plugin-prettier'

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    name: 'bikemaster/custom',
    languageOptions: {
      globals: {
        browser: true,
        node: true,
        vitest: true,
      },
    },
  },
  {
    name: 'bikemaster/rules',
    plugins: {
      prettier: pluginPrettier,
    },
    rules: {
      'prettier/prettier': 'warn',
      'vue/multi-word-component-names': ['error', { ignores: ['ToastContainer'] }],
    },
  },
]
