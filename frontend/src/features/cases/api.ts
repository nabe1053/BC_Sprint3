import { unwrapSuccess } from "@/shared/api/unwrap";
/**
 * features/cases/api.ts — Data Access（orval 生成の薄いラッパー）。
 *
 * 生成コード（`shared/api/generated/ui.ts`）を直接 features/hooks.ts から呼ばず、
 * ここで一段ラップする（依存ルール: features → shared/api/generated）。
 * 非2xx は customInstance が ApiError として投げるので、ここでは変換しない。
 */
import {
  createCaseApiV1UiCasesPost,
  getCaseApiV1UiCasesCaseIdGet,
  listCasesApiV1UiCasesGet,
  listRecordsApiV1UiVersionsVersionIdRecordsGet,
} from "@/shared/api/generated/ui";
import type {
  CaseCreateRequest,
  CaseListItem,
  CaseResponse,
  RecordsResponse,
} from "@/shared/api/generated/model";

export async function listCases(): Promise<CaseListItem[]> {
  const response = await listCasesApiV1UiCasesGet();
  return unwrapSuccess(response, 200).cases;
}

export async function createCase(
  input: CaseCreateRequest,
): Promise<CaseResponse> {
  const response = await createCaseApiV1UiCasesPost(input);
  return unwrapSuccess(response, 201);
}

export async function getCase(caseId: number): Promise<CaseResponse> {
  return unwrapSuccess(await getCaseApiV1UiCasesCaseIdGet(caseId), 200);
}

/** F-15: 案件一覧の行を展開したときの版の記録（#28）。 */
export async function listVersionRecords(
  versionId: number,
): Promise<RecordsResponse> {
  return unwrapSuccess(
    await listRecordsApiV1UiVersionsVersionIdRecordsGet(versionId),
    200,
  );
}
