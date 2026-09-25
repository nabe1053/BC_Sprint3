/**
 * 記録日時の表示形式。API は timestamptz を ISO 文字列で返すため、画面では
 * 日本時間（Asia/Tokyo）の分までに揃える（memory AD-036 ⑤）。
 * 見積期限（quoteDeadline）は原表記を示す方針のため、この関数を通さない。
 */
const FORMAT = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

export const EMPTY_DATETIME = "—";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return EMPTY_DATETIME;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return EMPTY_DATETIME;
  const p = Object.fromEntries(
    FORMAT.formatToParts(date).map(({ type, value }) => [type, value]),
  );
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}`;
}
