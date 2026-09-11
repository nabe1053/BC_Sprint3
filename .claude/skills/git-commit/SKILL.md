---
name: git-commit
description: コード品質チェック（formatter/linter/test）を実行してから git commit する
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
---

# git-commit: コード品質チェック & Commit

コードの品質を確保してから git commit を実行するスキル。
Frontend（Next.js + React）と Backend（FastAPI + Python）の両方をチェックする。

## 技術スタック（Sprint 3 固定）

```
Frontend（Node.js + Next.js 15 + React）
  ├─ Prettier（formatter）
  ├─ ESLint（linter・next lint）
  ├─ TypeScript チェック
  └─ Jest テスト

Backend（Python + FastAPI）
  ├─ ruff format（formatter）
  ├─ ruff check（linter）
  └─ pytest テスト
```

## Procedure

### Step 1: 変更内容確認

```bash
git status
git diff --stat
```

変更ファイルをユーザーに表示し、コミット対象を確認する。

### Step 2: Frontend チェック（frontend/ が変更されている場合）

```bash
# Formatter（自動修正）
cd frontend && npx prettier --write "src/**/*.{ts,tsx}"

# Linter
cd frontend && npm run lint

# TypeScript 型チェック
cd frontend && npm run typecheck

# テスト（Jest）
cd frontend && npm run test
```

エラーがあれば詳細を表示し、ユーザーに修正を促す。
すべて成功したら Step 3 へ。

### Step 3: Backend チェック（backend/ が変更されている場合）

```bash
# Formatter（自動修正）
cd backend && uv run ruff format app tests

# Linter（自動修正）
cd backend && uv run ruff check --fix app tests

# テスト
cd backend && uv run pytest tests/ -v
```

エラーがあれば詳細を表示し、ユーザーに修正を促す。
すべて成功したら Step 4 へ。

### Step 4: Git commit 実行

```bash
git add -A
git commit -m "{COMMIT_MESSAGE}"
```

コミットメッセージは以下の優先順で生成：
1. ユーザーが指定した場合 → そのまま使用
2. 指定がない場合 → `git diff --stat` からの内容を元に自動生成

**メッセージテンプレート**:
```
{type}: {brief description}

- {変更ファイルや内容の箇条書き}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

type の例: `feat`, `fix`, `refactor`, `test`, `chore`

### Step 5: 完了メッセージ

```
✅ すべてのチェックが合格しました

実行したチェック：
- Prettier / ruff format（formatter）
- ESLint / ruff check（linter）
- TypeScript / pytest（テスト）

✅ Commit: {COMMIT_HASH}

次のステップ：
- git push でリモートにプッシュ
- または続けて実装を進める
```

## Constraints

- **チェック失敗時**: commit は実行しない。エラー詳細を表示してユーザーに修正を促す
- **formatter 自動修正時**: 修正されたファイルを表示し、ユーザーが確認してから commit
- **変更なし**: `git status` が clean の場合はその旨を伝え終了
