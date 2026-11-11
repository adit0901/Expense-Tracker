import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'playwright-report', 'test-results', 'src/types/api.d.ts'] },
  { files: ['e2e/**/*.ts', 'playwright.config.ts'], languageOptions: { globals: globals.node } },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: { ecmaVersion: 2023, globals: globals.browser },
    plugins: { 'react-hooks': reactHooks, 'react-refresh': reactRefresh },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Feature modules co-locate hooks/helpers with components; this only affects dev HMR
      // granularity (a full reload instead of a hot swap), so it is not enforced.
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    files: ['src/components/ui/**/*.tsx', 'src/test/**', 'src/**/*.test.{ts,tsx}', 'src/app/**'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
)
