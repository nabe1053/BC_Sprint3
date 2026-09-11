#!/usr/bin/env node
// design-lint: デザイントークン逸脱の軽量サニティチェック。
// 「おかしなことをしていないか」だけを機械検出する（デザインの良し悪しは判定しない）。
// ルールの根拠: .claude/rules/design-guidelines.md / トークンの真実源: docs/requirements/03-spec.md 3章
//
// 使い方:
//   node .claude/scripts/design-lint.mjs          # プロジェクト全体をスキャン（品質ゲート用）
//   node .claude/scripts/design-lint.mjs --hook   # PostToolUse フック用（stdin の file_path のみ検査）
//
// 終了コード: 0=違反なし（警告のみ含む） / 1=違反あり / フックモードでは違反ありのとき 2（Claude に差し戻し）

import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { join, extname } from 'node:path'

const HOOK_MODE = process.argv.includes('--hook')

// トークン定義ファイル（hex 直書きを許可する場所）
const TOKEN_FILE = /(shared\/theme\/tokens\.ts|tailwind\.config\.(ts|js))$/
// スキャン対象外
const IGNORE_DIR = /(node_modules|\.next|dist|build|coverage|generated)(\/|$)/
const TARGET_EXT = new Set(['.ts', '.tsx', '.jsx'])

const RULES = [
  {
    id: 'mui-default-color',
    level: 'error',
    // トークンファイル内でも禁止（「素のMUI」デフォルト値の残存）
    everywhere: true,
    re: /#(1976d2|9c27b0)\b/i,
    msg: 'MUI デフォルト色（#1976d2 / #9c27b0）が残っている。03-spec 3章のトークン値に置き換える',
  },
  {
    id: 'hardcoded-hex',
    level: 'error',
    re: /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/,
    msg: 'hex カラーの直書き。デザイン値はトークン（tokens.ts / tailwind.config.ts）経由で使う',
  },
  {
    id: 'tailwind-default-palette',
    level: 'error',
    re: /\b(?:bg|text|border|ring|from|to|fill|stroke|divide|outline)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/,
    msg: 'Tailwind デフォルトパレットのクラス。theme.extend で定義したトークン由来のクラス（main-* 等）を使う',
  },
  {
    id: 'tailwind-arbitrary-value',
    level: 'error',
    re: /\b(?:bg|text|border|rounded|p[trblxy]?|m[trblxy]?|w|h|gap|inset|top|left|right|bottom|leading|tracking)-\[[^\]]+\]/,
    msg: 'Tailwind 任意値クラス（例: bg-[#123456]）。トークン由来のクラスのみ使う',
  },
  {
    id: 'inline-style',
    level: 'warn',
    re: /style=\{\{/,
    msg: 'インライン style。デザイン指定ならトークン経由（sx/クラス）に寄せる',
  },
]

function lintFile(path) {
  const findings = []
  let text
  try {
    text = readFileSync(path, 'utf8')
  } catch {
    return findings
  }
  const isTokenFile = TOKEN_FILE.test(path)
  const lines = text.split('\n')
  for (const rule of RULES) {
    if (isTokenFile && !rule.everywhere) continue
    lines.forEach((line, i) => {
      if (rule.re.test(line)) {
        findings.push({ path, line: i + 1, rule, snippet: line.trim().slice(0, 100) })
      }
    })
  }
  return findings
}

function walk(dir, acc) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (IGNORE_DIR.test(p)) continue
    const st = statSync(p)
    if (st.isDirectory()) walk(p, acc)
    else if (TARGET_EXT.has(extname(p))) acc.push(p)
  }
  return acc
}

function report(findings) {
  const errors = findings.filter((f) => f.rule.level === 'error')
  const warns = findings.filter((f) => f.rule.level === 'warn')
  for (const f of findings) {
    const mark = f.rule.level === 'error' ? '✗' : '△'
    console.log(`${mark} ${f.path}:${f.line} [${f.rule.id}] ${f.rule.msg}`)
    console.log(`    ${f.snippet}`)
  }
  if (findings.length === 0) {
    console.log('✓ design-lint: 違反なし')
  } else {
    console.log(`\ndesign-lint: エラー ${errors.length} 件 / 警告 ${warns.length} 件`)
  }
  return errors.length
}

if (HOOK_MODE) {
  // PostToolUse フック: stdin の JSON から編集ファイルを特定し、そのファイルだけ検査する
  let input = ''
  process.stdin.on('data', (d) => (input += d))
  process.stdin.on('end', () => {
    let filePath
    try {
      filePath = JSON.parse(input)?.tool_input?.file_path
    } catch {
      process.exit(0)
    }
    if (!filePath || !TARGET_EXT.has(extname(filePath)) || IGNORE_DIR.test(filePath)) process.exit(0)
    if (!existsSync(filePath)) process.exit(0)
    const findings = lintFile(filePath)
    const errorCount = findings.filter((f) => f.rule.level === 'error').length
    if (findings.length > 0) {
      // exit 2 の stderr は Claude に差し戻される
      for (const f of findings) {
        console.error(`design-lint ${f.rule.level}: ${f.path}:${f.line} ${f.rule.msg}`)
      }
    }
    process.exit(errorCount > 0 ? 2 : 0)
  })
} else {
  const roots = ['frontend/src', 'src'].filter((d) => existsSync(d))
  if (roots.length === 0) {
    console.log('design-lint: スキャン対象（frontend/src または src）が見つからないためスキップ')
    process.exit(0)
  }
  const files = roots.flatMap((r) => walk(r, []))
  const findings = files.flatMap(lintFile)
  const errorCount = report(findings)
  process.exit(errorCount > 0 ? 1 : 0)
}
