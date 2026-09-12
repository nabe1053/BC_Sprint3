/**
 * Orval Custom Mutator (Fetch API版)
 *
 * orval が生成する API クライアントで使うカスタムインスタンス。
 *
 * **認証は実装しない**（CLAUDE.md 決定事項1 / 02-requirement.md N02）。
 * ローカル単一利用者の PoC であり、担当者・上司は記録上の役割でアクセス制御ではない。
 * したがってトークン更新・401 リトライ・ログインへのリダイレクトを**持たない**。
 * 401 が返るのは実装の誤りであり、他のエラーと同じく呼び出し元へ投げて可視化する。
 *
 * エラー形は API 共通の `{ code, message, details }`（05-api-ipo.md 0.2・6章）。
 * `code` の意味は 05-api-ipo.md 6章のエラーコード一覧が SSOT。
 *
 * @see https://orval.dev/reference/configuration/output#mutator
 */

// Next.js: ブラウザに公開する環境変数は NEXT_PUBLIC_ プレフィックス（.env.local で設定）
const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
export const apiBaseUrl = baseURL;

/** API が返す共通エラー形（05-api-ipo.md 0.2） */
export type ApiErrorBody = {
  code: string;
  message: string;
  details?: unknown;
};

/** 呼び出し元で `code` を見て分岐できるようにするためのエラー */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, body: Partial<ApiErrorBody>) {
    super(body.message ?? `API error (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code ?? "E_UNKNOWN";
    this.details = body.details;
  }
}

/**
 * カスタムインスタンス（orval用）
 *
 * - Content-Type を必要なときだけ付ける
 * - 非 2xx は `ApiError`（`code` つき）として投げる。**リトライもリダイレクトもしない**
 * - 204 / 本文なしは `undefined` を返す
 */
export const customInstance = async <T>(
  url: string,
  options?: RequestInit,
): Promise<T> => {
  const headers = new Headers(options?.headers);

  if (
    !headers.has("Content-Type") &&
    options?.body &&
    typeof options.body === "string"
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${baseURL}${url}`, { ...options, headers });

  const isJson = (response.headers.get("Content-Type") ?? "").includes(
    "application/json",
  );
  const body = isJson
    ? await response.json().catch(() => undefined)
    : undefined;

  if (!response.ok) {
    throw new ApiError(response.status, (body ?? {}) as Partial<ApiErrorBody>);
  }

  return {
    data: body,
    status: response.status,
    headers: response.headers,
  } as T;
};

/**
 * エラー型（orval用）。TanStack Query の error 型として使われる。
 */
export type ErrorType<E> = E & { message?: string };

/**
 * Body型（orval用）
 */
export type BodyType<B> = B;
