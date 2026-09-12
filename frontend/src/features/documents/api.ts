import { unwrapSuccess } from "@/shared/api/unwrap";
/**
 * features/documents/api.ts — Data Access（orval 生成の薄いラッパー）。
 *
 * AD-008: SCR-02 は Build では実 API（#4 一覧・#5 投入）を使う。
 */
import {
  intakeDocumentApiV1UiCasesCaseIdDocumentsPost,
  listDocumentsApiV1UiCasesCaseIdDocumentsGet,
} from "@/shared/api/generated/ui";
import type {
  DocumentIntakeResponse,
  DocumentSummary,
} from "@/shared/api/generated/model";

export async function listDocuments(
  caseId: number,
): Promise<DocumentSummary[]> {
  const response = await listDocumentsApiV1UiCasesCaseIdDocumentsGet(caseId);
  return unwrapSuccess(response, 200).documents;
}

export async function intakeDocument(
  caseId: number,
  file: File,
): Promise<DocumentIntakeResponse> {
  const response = await intakeDocumentApiV1UiCasesCaseIdDocumentsPost(caseId, {
    file,
  });
  return unwrapSuccess(response, 201);
}
