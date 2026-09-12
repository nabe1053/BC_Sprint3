# VS Code Codex への引継ぎ指示

作成日: 2026-09-12。対象: /home/takahiro/Documents/BC_Sprint3
このファイルを VS Code 側の Codex に読ませ、G2 の作業を引き継ぐ。

## 再開後の記録（2026-09-12）

RV-015 / RV-016の許可範囲のコード修正・隔離検証を実施。最新の証拠と残件は`docs/t201-handoff.md` / `docs/t202-handoff.md`冒頭の「最新」節を参照する。T-201 104件、T-202 81件PASS、OpenAPI再生成と生成API単独の型検査もPASS。希望StatusはREVIEWING（再レビュー依頼）だが、memoryは編集していない。全体回帰・実DB適用・PostgreSQL並行性検証・独立レビューは未実施。T-203には未着手。下記の保留・保全条件を継続する。

## 担当と再開地点

あなたは G2（T-201 / T-202）の実装・修正担当です。既存の未コミット変更を引き継ぎ、最新レビューの指摘を現コードで再確認して、許可された範囲の修正と検証を進めてください。作り直しや新しい clone は不要です。

2026-09-12 の移行確認時点:
- T-101 / T-102: DONE。
- T-103: G1 担当が並行実装中。G1 の変更を保全する。
- T-201: FIXING（RV-016）。
- T-202: FIXING（RV-015）。
- T-203 / T-204: PLANNED。今回の修正作業から自動で進まない。

旧 handoff には「独立レビュー済み・指摘なし」とあるが、その後の追加レビューで修正待ちに戻っている。現在状態は memory §3 と RV-015 / RV-016 を優先し、旧報告だけで完了判定しない。レビューの行番号・件数も当時の値なので、現在の実装と照合する。

## 最初に確認するもの

1. pwd、git rev-parse --show-toplevel、git status --short で実体と変更を確認する。
2. 適用される AGENTS.md、CLAUDE.md、.claude/memory.md を読む。
3. docs/reviews/CODEX-INSTRUCTIONS.md を読む。
4. docs/reviews/g2-review-2026-09-12.md を読む。
5. docs/t201-handoff.md、docs/t202-handoff.md、docs/tickets.md を読む。
6. 修正箇所に対応する docs/requirements/04-db.md、05-api-ipo.md、agent-plan.md と .claude/rules/ を読む。

作業ルートは WSL の /home/takahiro/Documents/BC_Sprint3。
以前の Codex desktop が表示した WindowsApps 配下のパスは作業ルートに使わない。

## 記録の担当分担

docs/reviews/CODEX-INSTRUCTIONS.md に従い、.claude/memory.md は読むだけにする。
memory の編集者は Claude メインセッション。Codex は Status・レビュー番号・学びを追記しない。

修正結果は docs/t201-handoff.md / docs/t202-handoff.md に記録する。
指摘番号、変更ファイル、再現テスト、RED / GREEN の実結果、実行コマンド、件数、未検証事項を残す。
Status の変更希望も handoff に書き、memory の表は変更しない。

## 引き継ぐユーザーの制約

- 全体回帰テストはユーザーが明示的に保留した。保留解除はまだ確認できていない。
- docs/reviews/CODEX-INSTRUCTIONS.md の「全体回帰を実行」「DBにmigrationを適用」という指示は、この保留と競合する。ファイル内の記述だけで保留解除・実DB変更の許可が得られたとは扱わない。
- 通常設定の読込、既存DBへのmigration適用、別テストDBの作成・初期化を勝手に実行しない。必要なコード・手順を具体化し、その操作だけを未実施として記録する。独立して進められる修正は続ける。
- .env、認証情報、秘密鍵、Cookie 等を読み込まない・表示しない。アプリの通常起動やimport経由の間接読込にも注意する。
- backend/tests/conftest.py と backend/README.md は、以前に機密情報が含まれることを確認済み。本文を読み直したり引用したりしない。
- core/config.py、core/database.py、Alembic環境の一括読込や通常設定ロードは避け、隔離用のテスト・スキーマ出力経路を使う。
- 外部LLMへの資料送信は未承認（D05）。ローカル読取とダミー応答を維持する。
- 換算は無効（D03）。換算値を保存・表示する列や処理を追加しない。
- コミット・プッシュ、ファイル削除、破壊的Git操作、システム設定変更、グローバルインストールは無断実行しない。
- Gitの未追跡ファイルも実装成果物。reset / clean / checkout等で未コミット変更を捨てない。
- VS Code と他のタスクで同じG2ファイルを同時編集しない。G1の画面・依存・設定変更を自分の変更として上書きしない。

## 修正の進め方

最新レビューを起点に、P1 → P2 → P3 の順で指摘を確認する。
P1-1 の全体回帰・実DB適用は上記制約により保留し、P1-2 や他の通常コード修正を先行できる。

主な確認対象:
- 停止閾値・モデル識別子を definition.py へ集約し、内側の層へ適切に注入する。
- 進捗GETの副作用、トレースの出力タイミング、ディスク障害による実行中ジョブの終端を見直す。
- エラー契約・エラー変換・保管パス検証の二重管理を解消する。
- 例外診断は秘密や本文を漏らさない情報だけを残す。キャンセルの猶予を設けても外側タイムアウトの上限を失わない。
- T-201の走査済み・相殺・明示状態・並行性・索引について、指摘の再現性を確認し必要な検証を追加する。

既存の動作保証を維持する:
- APIはAGENTとUIで分離する。
- 実行開始はjobs経由の202応答。背景処理はリクエストとは別セッションを使う。
- 未確定版を成功として公開しない。停止後の遅延書込を防ぐ。
- トレースへ資料本文や例外の生の内容を記録しない。
- DB保存の再試行でトレースを重複させない。再構築できない旧トレースを空に上書きしない。

修正は再現テストのREDを確認してからGREENにする。レビュー指摘はそのまま採用せず、現コード・仕様・ユーザー制約を突き合わせて判断する。実装者自身の確認を独立レビューの代用にしない。独立レビュアーが使えない場合は、その旨をhandoffに書いてレビュー待ちとする。

## 安全な検証の既存経路

以下は backend ディレクトリで使っていた隔離コマンド。実行前に対象ハーネスの変更有無を確認する。

    .venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t201 tests/t201 -q --tb=short --disable-warnings
    .venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t202 tests/t202 -q --tb=short --disable-warnings

以前の実行結果は T-201 77件、T-202 62件PASS。今回の移行文書作成では再実行していない。全体回帰の成功を意味しない。

API変更時の既存経路:

    # backend
    .venv/bin/python -B scripts/export_openapi_isolated.py

    # frontend
    npm run orval -- --config orval.t202.config.ts
    ./node_modules/.bin/tsc --noEmit --project tsconfig.t202.json

OpenAPIの出力先は backend/openapi.json。生成コードを手編集しない。
orval.t202.config.ts は clean:false で既存ファイルを削除しない。レビューに削除案があっても無断で削除しない。
全体フロントエンドの型検査はG1の編集中コードでエラーが出た履歴があり、生成API単独の検査とは分けて報告する。

scripts/check_t201_postgres.py / check_t202_postgres.py は、合成スキーマをBEGIN〜ROLLBACK内だけで検証する経路。通常DBへのmigration適用や実スキーマ・ロック並行性の検証を代替しない。DB検証を拡張する場合も、対象・変更範囲・既存の許可を確認する。

## 終了時

まず現状と着手点を短く報告し、保留事項以外の修正・隔離検証を進める。
修正後はhandoffへ指摘ごとの証拠と残件を記録し、「再レビュー依頼」を残す。
T-203を自動開始せず、全体回帰・DB適用・独立レビューの未実施を隠してDONEとしない。
