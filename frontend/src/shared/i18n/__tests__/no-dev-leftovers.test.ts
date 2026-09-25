/**
 * F-12 RED: 利用者に見える文言に、開発用の残骸（画面 ID・設計書名・スコープ外の印・模擬期の注記）を
 * 残さない（2026-09-24 研修者の修正依頼「余計な表示が各所に残っている」・memory AD-036 ⑤）。
 */
import ja from "../ja.json";

function values(node: unknown, path = ""): [string, string][] {
  if (typeof node === "string") return [[path, node]];
  if (node && typeof node === "object")
    return Object.entries(node).flatMap(([k, v]) =>
      values(v, path ? `${path}.${k}` : k),
    );
  return [];
}

it.each([
  ["画面 ID", /SCR-\d/],
  ["設計書名", /\d\d-spec|0[1-6] \/ 0/],
  ["スコープ外の印", /Scope 2/],
  ["スプリント名", /SPRINT/i],
  ["設計上の決定 ID", /\bD0\d\b/],
  ["模擬期の注記", /実ファイルを抽出する処理ではありません/],
])("%s を含む文言が無い", (_label, pattern) => {
  const hits = values(ja).filter(([, v]) => pattern.test(v));
  expect(hits).toEqual([]);
});

it("内部の資料番号・ms 表記の文言が無い", () => {
  const hits = values(ja).filter(([, v]) => /資料番号|\bms\b/.test(v));
  expect(hits).toEqual([]);
});
