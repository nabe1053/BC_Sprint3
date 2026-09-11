# OCTG Item List Agent - Frontend (Next.js 15)

Next.js 15（App Router）+ Material-UI + TanStack Query によるフロントエンド。

## セットアップ
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev   # http://localhost:3000
```

## 開発コマンド
- `npm run dev`: 開発サーバー起動
- `npm run build`: 本番ビルド
- `npm run test`: Jest テスト
- `npm run typecheck`: 型チェック
- `npm run orval`: OpenAPI から API client + フックを再生成（backend/openapi.json が必要）

## 構造
- `app/`: ページ（Server Component。UI 実体は features に置き薄く保つ）
- `features/`: 機能単位（api.ts / hooks.ts / components/ / index.ts）
- `shared/api/generated/`: orval 自動生成（編集禁止）
- `shared/{ui,hooks,lib,theme,i18n}/`: 横断モジュール

## ルール
- Client Component には "use client" を明示
- JSX 内に日本語を直接書かない（t() を使用）
- feature 間の直接 import 禁止（index.ts 経由）
- デザイントークンの真実源は `docs/requirements/03-spec.md` 3章（`shared/theme/tokens.ts` はその転記）

## 認証について
Sprint 3 は認証を実装しない（`02-requirement.md` N02）。`shared/api/mutator.ts` は Cookie 透過の
実装を含むが、未使用のため無害（変更不要）。
