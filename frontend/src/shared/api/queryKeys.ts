/**
 * feature をまたいで無効化するクエリキー（F-14）。
 * 案件一覧（#1）は案の作成が終わると最新版・件数が変わるため、agent-runs から無効化する。
 */
export const CASES_QUERY_KEY = ["cases"] as const;
