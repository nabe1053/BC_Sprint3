import { dirname } from 'path'
import { fileURLToPath } from 'url'
import { FlatCompat } from '@eslint/eslintrc'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const compat = new FlatCompat({ baseDirectory: __dirname })

const config = [
  {
    // orval が生成するコード・ビルド成果物は lint 対象外（手で直さないため）
    ignores: [
      'node_modules/**',
      '.next/**',
      'out/**',
      'coverage/**',
      'src/shared/api/generated/**',
      'jest.config.js',
      'jest.setup.js',
      // Next.js が生成する型参照ファイル（手で直さない）
      'next-env.d.ts',
    ],
  },
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  {
    rules: {
      // デザイン値のハードコード禁止は .claude/scripts/design-lint.mjs が担当する
      // （ESLint では色・余白のセマンティクスを判定できない）
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
]

export default config
