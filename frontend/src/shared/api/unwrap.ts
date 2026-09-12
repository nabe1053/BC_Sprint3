import { ApiError } from "./mutator";

/** orvalのstatus付きユニオンを成功本文へ絞る唯一の境界。
 * 通常の非2xxはmutatorでthrowされる。想定外の応答も成功として流さない。
 */
export function unwrapSuccess<
  R extends { status: number; data: unknown },
  S extends R["status"],
>(response: R, status: S): Extract<R, { status: S }>["data"] {
  if (response.status !== status) {
    throw new ApiError(response.status, { code: "E_UNEXPECTED_RESPONSE" });
  }
  // TypeScriptはジェネリックSとstatusの等価比較だけではExtractまで推論しない。
  return response.data as Extract<R, { status: S }>["data"];
}
