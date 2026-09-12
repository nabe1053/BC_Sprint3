import { alpha } from "@mui/material/styles";

/** MUI v5のJS色演算用。トークンのsrgb＋透明色の混合を同値のrgbaへ変換する。
 * CSSで直接使うトークンは変更せず、色・濃度を新たに定義しない。
 */
export function muiColor(value: string): string {
  const mix =
    /^color-mix\(in srgb,\s*(#[\da-f]{6})\s+(\d+)%,\s*transparent\)$/i.exec(
      value,
    );
  return mix ? alpha(mix[1], Number(mix[2]) / 100) : value;
}
