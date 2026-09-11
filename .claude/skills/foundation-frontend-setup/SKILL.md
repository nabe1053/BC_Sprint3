---
name: foundation-frontend-setup
description: Next.js 15 (App Router) + Material-UI フロントエンド初期化・ディレクトリ構造・開発環境設定
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Slice 0-5: Frontend Setup (Next.js 15 + MUI)

Next.js 15（App Router）+ Material-UI フロントエンドの初期化・ディレクトリ構造構築・開発環境設定を行うスキル。

## Purpose

フロントエンド開発を始めるための基盤を整備する：

1. Next.js 15（App Router）プロジェクトの構成（配置済み package.json ベース）
2. ディレクトリ構造の作成（Feature-Sliced Design + 3レイヤー）
3. Material-UI v5 + `@mui/material-nextjs` の設定
4. TanStack Query の設定（Client Component 内で使用）
5. Jest + React Testing Library の設定
6. i18n（react-i18next）の初期設定
7. orval 設定の確認（OpenAPI から API client + フックを自動生成）

## When to use

- Slice 0-1 ～ 0-4（バックエンド基盤）が完了した後に実行
- フロントエンド全体の基盤を整備したい

## Prerequisites

- Slice 0-1 ～ 0-4 が完了していること
- Node.js v18+ がインストールされていること
- `/r2b-build-sprint3` により以下が**配置済み・インストール済み**であること：
  - `frontend/package.json`（Next.js 15 / React 19 / MUI / TanStack Query / Jest / orval）
  - `frontend/orval.config.ts`（生成先 `src/shared/api/generated/`・react-query クライアント）
  - `frontend/src/shared/api/mutator.ts`（Cookie 認証・トークン自動更新）

> **注意**: `npm create next-app` は実行しない（配置済み package.json を上書きしてしまう）。
> このスキルはディレクトリと設定ファイルを手で組み立てる。

## Outputs

プロジェクト構造（`CLAUDE.md` の「ディレクトリ構造」と一致させる）：
```
frontend/
├── src/
│   ├── app/                         # App Router
│   │   ├── layout.tsx               # Root layout（providers を適用）
│   │   ├── providers.tsx            # Client Component（MUI + TanStack Query）
│   │   ├── page.tsx                 # Root page
│   │   ├── (auth)/
│   │   │   └── login/page.tsx       # ログイン（プレースホルダ）
│   │   └── (portal)/
│   │       └── dashboard/page.tsx   # ダッシュボード（プレースホルダ）
│   ├── features/                    # Feature-Sliced Design（Phase 1 以降に追加）
│   ├── shared/
│   │   ├── api/
│   │   │   ├── generated/           # orval 自動生成（編集禁止・git管理外）
│   │   │   └── mutator.ts           # 配置済み
│   │   ├── ui/                      # 汎用 UI（Rule of Three で抽出）
│   │   ├── hooks/                   # 横断カスタム hooks
│   │   ├── lib/                     # 純粋関数（queryClient など）
│   │   ├── theme/
│   │   │   └── tokens.ts            # デザイントークン
│   │   └── i18n/
│   │       ├── index.ts             # i18next 初期化
│   │       └── ja.json              # 翻訳ファイル
│   └── entities/                    # ドメインエンティティ（必要時）
├── jest.config.ts
├── jest.setup.ts
├── next.config.ts
├── tsconfig.json
├── .env.local.example
├── package.json                     # 配置済み
├── orval.config.ts                  # 配置済み
└── README.md
```

## Procedure

### Step 1: 環境・配置済みファイルの確認

```bash
node --version   # v18+
cd frontend
ls package.json orval.config.ts src/shared/api/mutator.ts
npm ls next @mui/material @tanstack/react-query jest 2>/dev/null | head
```

不足があれば `/r2b-build-sprint3` の再実行 or `npm install` を案内する。

### Step 2: ディレクトリ構造を作成

```bash
cd frontend
mkdir -p "src/app/(auth)/login" "src/app/(portal)/dashboard"
mkdir -p src/features
mkdir -p src/shared/api src/shared/ui src/shared/hooks src/shared/lib src/shared/theme src/shared/i18n
mkdir -p src/entities
```

### Step 3: TypeScript / Next.js 設定

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

```typescript
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
}

export default nextConfig
```

### Step 4: テーマとデザイントークン

**まず `docs/requirements/03-spec.md` の「3. デザイントークン」を読む**（デザインの真実源）。
以下の `#___` をその表の値で置き換えて生成する。デザイン規約は `.claude/rules/design-guidelines.md` を参照。
（03-spec に3章が無い旧設計の場合は、研修者に確認してトークンを決めてから進める）

```typescript
// src/shared/theme/tokens.ts
// デザイン値のハードコード禁止。色・余白・タイポはここを経由する。
// 値の真実源は docs/requirements/03-spec.md「3. デザイントークン」（このファイルは転記）
export const tokens = {
  colors: {
    // 色相は main と error の2つだけ。他はすべて濃淡（design-guidelines 参照）
    main: {
      100: '#___', // 淡い背景・ホバー
      300: '#___', // 枠線・補助
      500: '#___', // 主要アクション・強調
      700: '#___', // アクションのホバー・アクティブ
      900: '#___', // 濃い強調
    },
    background: '#___', // ページ背景（純白禁止）
    surface: '#___',    // カード・パネル背景
    text: {
      primary: '#___',   // 純黒禁止
      secondary: '#___',
      meta: '#___',
    },
    error: '#___',
  },
  typography: {
    fontHeading: '___', // 03-spec の font-heading（日本語フォールバック込みのスタック）
    fontBody: '___',    // 03-spec の font-body
  },
  radius: 0, // 03-spec の radius（px）
  spacing: (n: number) => n * 8,
} as const
```

### Step 5: Providers（Client Component）と Root Layout

TanStack Query・MUI は **Client Component** でのみ動くため、providers に隔離して
Root Layout（Server Component）から適用する：

```tsx
// src/app/providers.tsx
'use client'

import { useState, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter'
import { tokens } from '@/shared/theme/tokens'
import '@/shared/i18n'

// 脱・標準MUI の必須設定（.claude/rules/design-guidelines.md 参照）。
// デフォルトの青 #1976d2・紫 #9c27b0・Roboto・大文字ボタンを残さない
const theme = createTheme({
  palette: {
    primary: {
      light: tokens.colors.main[300],
      main: tokens.colors.main[500],
      dark: tokens.colors.main[700],
    },
    secondary: { main: tokens.colors.main[700] },
    error: { main: tokens.colors.error },
    background: {
      default: tokens.colors.background,
      paper: tokens.colors.surface,
    },
    text: {
      primary: tokens.colors.text.primary,
      secondary: tokens.colors.text.secondary,
    },
  },
  typography: {
    fontFamily: tokens.typography.fontBody,
    h1: { fontFamily: tokens.typography.fontHeading },
    h2: { fontFamily: tokens.typography.fontHeading },
    h3: { fontFamily: tokens.typography.fontHeading },
  },
  shape: { borderRadius: tokens.radius },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { textTransform: 'none' } },
    },
    // 影の重なりを避ける（design-guidelines: 影は1段階まで・枠線を基本とする）
    MuiCard: { defaultProps: { variant: 'outlined' } },
  },
})

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false },
          mutations: { retry: 1 },
        },
      }),
  )

  return (
    <AppRouterCacheProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </QueryClientProvider>
    </AppRouterCacheProvider>
  )
}
```

> `@mui/material-nextjs` の import パスはインストールされている MUI バージョンに合わせる
> （v15-appRouter が無ければ v14-appRouter）。エラーになったら `npm ls @mui/material-nextjs` で確認。

```tsx
// src/app/layout.tsx
import type { Metadata } from 'next'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'R2B Training',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

### Step 6: ページのプレースホルダ

```tsx
// src/app/page.tsx（Server Component のまま）
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/dashboard')
}
```

```tsx
// src/app/(auth)/login/page.tsx
export default function LoginPage() {
  return <main>Login（Phase 1 で実装）</main>
}
```

```tsx
// src/app/(portal)/dashboard/page.tsx
export default function DashboardPage() {
  return <main>Dashboard（Phase 1 で実装）</main>
}
```

> 画面の実体は Phase 2 以降に `/build-loop` が
> `features/{name}/components/`（Client Component）として実装し、page.tsx は薄く保つ。

### Step 7: i18n（react-i18next）初期設定

**JSX 内に日本語を直接書かない**ルールの土台：

```typescript
// src/shared/i18n/index.ts
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import ja from './ja.json'

i18n.use(initReactI18next).init({
  resources: { ja: { translation: ja } },
  lng: 'ja',
  fallbackLng: 'ja',
  interpolation: { escapeValue: false },
})

export default i18n
```

```json
// src/shared/i18n/ja.json
{
  "common": {
    "loading": "読み込み中...",
    "error": "エラーが発生しました"
  }
}
```

### Step 8: Jest + React Testing Library を設定

`next/jest` を使うと Next.js の変換設定（SWC・パスエイリアス）を自動で引き継げる：

```typescript
// jest.config.ts
import type { Config } from 'jest'
import nextJest from 'next/jest.js'

const createJestConfig = nextJest({ dir: './' })

const config: Config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
}

export default createJestConfig(config)
```

```typescript
// jest.setup.ts
import '@testing-library/jest-dom'
```

> テストの書き方（jest.mock / jest.fn）は test-designer エージェント・`.claude/rules/tdd-guide.md` に準拠する。

### Step 9: orval 設定の確認と初回生成

`orval.config.ts` と `mutator.ts` は配置済み。設定の要点をユーザーに説明する：

- 生成先: `src/shared/api/generated/`（**編集禁止・git 管理外**）
- `mode: 'tags'`: タグごとにファイル分割（例: `generated/applications.ts`、型は `generated/model/`）
- `client: 'react-query'`: TanStack Query のフック（`useGetXxx`）を生成。
  features 側は `features/{name}/api.ts` でこのフックを wrap して使う
- `mutator`: Cookie 認証（credentials: include）と 401 時の自動リフレッシュ

```bash
# Backend の openapi.json が出力済みなら初回生成を試す（Slice 0-6 で本格実施）
ls ../backend/openapi.json && npm run orval || echo "openapi.json は Slice 0-6 で生成します"
```

### Step 10: 環境変数

```bash
# .env.local.example（コピーして .env.local を作る。NEXT_PUBLIC_ はブラウザに公開される）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

```bash
cp .env.local.example .env.local
```

### Step 11: README.md を作成

```markdown
# Training Sprint 3 - Frontend (Next.js 15)

Next.js 15（App Router）+ Material-UI + TanStack Query によるフロントエンド。

## セットアップ
\`\`\`bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev   # http://localhost:3000
\`\`\`

## 開発コマンド
- \`npm run dev\`: 開発サーバー起動
- \`npm run build\`: 本番ビルド
- \`npm run test\`: Jest テスト
- \`npm run typecheck\`: 型チェック
- \`npm run orval\`: OpenAPI から API client + フックを再生成

## 構造
- app/: ページ（Server Component。UI 実体は features に置き薄く保つ）
- features/: 機能単位（api.ts / hooks.ts / components/ / index.ts）
- shared/api/generated/: orval 自動生成（編集禁止）
- shared/{ui,hooks,lib,theme,i18n}/: 横断モジュール

## ルール
- Client Component には "use client" を明示
- JSX 内に日本語を直接書かない（t() を使用）
- feature 間の直接 import 禁止（index.ts 経由）
```

### Step 12: 動作確認

```bash
npm run typecheck
npm run test          # passWithNoTests でグリーンになる
npm run dev &         # http://localhost:3000 → /dashboard にリダイレクト
```

**確認項目**:
- [ ] `npm run typecheck` が成功する
- [ ] `npm run test` が成功する
- [ ] http://localhost:3000 が表示され /dashboard にリダイレクトされる
- [ ] MUI のスタイル（CssBaseline）が適用されている

## チェックリスト

### Slice 0-5 完了時

- [ ] ディレクトリ構造を作成した（app / features / shared / entities）
- [ ] tsconfig.json（paths @/*）・next.config.ts 作成完了
- [ ] Providers（AppRouterCacheProvider + QueryClientProvider + ThemeProvider）を
      Client Component として実装し、Root Layout から適用した
- [ ] ページプレースホルダ（/, (auth)/login, (portal)/dashboard）作成完了
- [ ] i18n 初期設定完了（src/shared/i18n/）
- [ ] Jest + React Testing Library 設定完了（next/jest）
- [ ] **⭐ orval.config.ts / mutator.ts は配置済み**（生成先 `src/shared/api/generated/`・
      react-query フック生成・Cookie 認証）であることを確認した
- [ ] .env.local 作成完了（NEXT_PUBLIC_API_BASE_URL）
- [ ] typecheck / test / dev サーバー起動確認完了
- [ ] README.md 作成完了

### 次のステップ

Slice 0-5 完了後は、**Slice 0-6: API Integration（OpenAPI 出力・orval 生成）を実行**

```
Slice 0-1: FastAPI セットアップ
Slice 0-2: PostgreSQL Docker
Slice 0-3: Database Design & Implementation
Slice 0-4: Authentication Middleware (JWT/Cookie)
  ↓
Slice 0-5（ここ）
  ↓
Slice 0-6: API Integration
  ↓
Slice 0-7: Agent Setup（Claude Agent SDK）
```

## 参考資料

- [Next.js Documentation](https://nextjs.org/docs)
- [MUI - Next.js App Router 統合](https://mui.com/material-ui/integrations/nextjs/)
- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [orval Documentation](https://orval.dev/)
- [Jest - Next.js Testing](https://nextjs.org/docs/app/building-your-application/testing/jest)
