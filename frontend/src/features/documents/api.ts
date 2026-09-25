import { unwrapSuccess } from "@/shared/api/unwrap";
/**
 * features/documents/api.ts — Data Access（orval 生成の薄いラッパー）。
 *
 * AD-008: SCR-02 は Build では実 API（#4 一覧・#5 投入）を使う。
 */
import {
  excludeDocumentApiV1UiCasesCaseIdDocumentsDocumentIdExclusionPost,
  intakeDocumentApiV1UiCasesCaseIdDocumentsPost,
  listDocumentExclusionsApiV1UiCasesCaseIdDocumentExclusionsGet,
  listDocumentsApiV1UiCasesCaseIdDocumentsGet,
} from "@/shared/api/generated/ui";
import type {
  DocumentExclusionRecord,
  DocumentIntakeResponse,
  DocumentSummary,
  ExcludedDocument,
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

/** F-16: 資料の除外（#5a）。物理削除ではなく除外の記録。 */
export async function excludeDocument(
  caseId: number,
  documentId: number,
  recordedBy: string,
): Promise<DocumentExclusionRecord> {
  return unwrapSuccess(
    await excludeDocumentApiV1UiCasesCaseIdDocumentsDocumentIdExclusionPost(
      caseId,
      documentId,
      { recordedBy },
    ),
    201,
  );
}

/** F-16: 除外済みの資料（#5b）。 */
export async function listDocumentExclusions(
  caseId: number,
): Promise<ExcludedDocument[]> {
  return unwrapSuccess(
    await listDocumentExclusionsApiV1UiCasesCaseIdDocumentExclusionsGet(caseId),
    200,
  ).exclusions;
}
