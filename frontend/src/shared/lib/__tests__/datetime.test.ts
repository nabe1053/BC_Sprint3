/**
 * F-12 RED: 日時は JST・分までで表示する（2026-09-24 研修者の修正依頼・memory AD-036 ⑤）。
 */
import { formatDateTime } from "../datetime";

it("UTC の ISO 文字列を JST の分まで（YYYY-MM-DD HH:mm）で返す", () => {
  expect(formatDateTime("2026-09-13T01:23:45Z")).toBe("2026-09-13 10:23");
});

it("JST で日付が繰り上がる時刻も正しく変換する", () => {
  expect(formatDateTime("2026-12-31T15:00:00Z")).toBe("2027-01-01 00:00");
});

it("オフセット付きの値も JST に揃える", () => {
  expect(formatDateTime("2026-09-13T09:00:00+09:00")).toBe("2026-09-13 09:00");
});

it("null・空・解釈できない値は代替表記（—）にする", () => {
  expect(formatDateTime(null)).toBe("—");
  expect(formatDateTime(undefined)).toBe("—");
  expect(formatDateTime("")).toBe("—");
  expect(formatDateTime("not-a-date")).toBe("—");
});
