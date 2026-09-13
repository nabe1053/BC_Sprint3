import { unwrapSuccess } from "@/shared/api/unwrap";
import { ApiError } from "@/shared/api/mutator";
import { parseExportFileName } from "./model";
import {
  listRecordsApiV1UiVersionsVersionIdRecordsGet,
  recordStateEventApiV1UiVersionsVersionIdStateEventsPost,
  recordBounceCommentApiV1UiVersionsVersionIdBounceCommentsPost,
  recordBounceApiV1UiVersionsVersionIdBouncesPost,
  recordSendoffDecisionApiV1UiVersionsVersionIdSendoffDecisionsPost,
  getInventoryApiV1UiVersionsVersionIdInventoryGet,
  listVersionsApiV1UiCasesCaseIdVersionsGet,
  getVersionApiV1UiVersionsVersionIdGet,
  listItemsApiV1UiVersionsVersionIdItemsGet,
  listEvidenceApiV1UiVersionsVersionIdItemsItemIdEvidenceGet,
  listQuestionsApiV1UiVersionsVersionIdQuestionsGet,
  editItemApiV1UiVersionsVersionIdEditsPost,
  undoEditApiV1UiVersionsVersionIdEditsEditIdUndoPost,
  confirmApiV1UiVersionsVersionIdConfirmationsPost,
  undoConfirmationApiV1UiVersionsVersionIdConfirmationsConfirmationIdUndoPost,
  judgeApiV1UiVersionsVersionIdQuestionsQuestionIdJudgementsPost,
  createExportApiV1UiVersionsVersionIdExportsPost,
  listExportsApiV1UiVersionsVersionIdExportsGet,
} from "@/shared/api/generated/ui";
import type {
  StateEventRequest,
  BounceCommentRequest,
  BounceRequest,
  SendoffDecisionRequest,
  ItemEditRequest,
  UndoRequest,
  ConfirmationRequest,
  JudgementRequest,
} from "@/shared/api/generated/model";

export async function listVersions(caseId: number) {
  return unwrapSuccess(
    await listVersionsApiV1UiCasesCaseIdVersionsGet(caseId),
    200,
  ).versions;
}
export async function getVersion(versionId: number) {
  return unwrapSuccess(
    await getVersionApiV1UiVersionsVersionIdGet(versionId),
    200,
  );
}
export async function listItems(versionId: number) {
  return unwrapSuccess(
    await listItemsApiV1UiVersionsVersionIdItemsGet(versionId),
    200,
  ).items;
}
export async function listQuestions(versionId: number) {
  return unwrapSuccess(
    await listQuestionsApiV1UiVersionsVersionIdQuestionsGet(versionId),
    200,
  ).questions;
}
export async function listEvidence(versionId: number, itemId: number) {
  return unwrapSuccess(
    await listEvidenceApiV1UiVersionsVersionIdItemsItemIdEvidenceGet(
      versionId,
      itemId,
    ),
    200,
  ).evidences;
}
export async function editItem(versionId: number, input: ItemEditRequest) {
  return unwrapSuccess(
    await editItemApiV1UiVersionsVersionIdEditsPost(versionId, input),
    201,
  ).edits;
}
export async function undoEdit(
  versionId: number,
  editId: number,
  input: UndoRequest,
) {
  return unwrapSuccess(
    await undoEditApiV1UiVersionsVersionIdEditsEditIdUndoPost(
      versionId,
      editId,
      input,
    ),
    200,
  );
}
export async function confirm(versionId: number, input: ConfirmationRequest) {
  return unwrapSuccess(
    await confirmApiV1UiVersionsVersionIdConfirmationsPost(versionId, input),
    201,
  );
}
export async function undoConfirmation(
  versionId: number,
  confirmationId: number,
  input: UndoRequest,
) {
  return unwrapSuccess(
    await undoConfirmationApiV1UiVersionsVersionIdConfirmationsConfirmationIdUndoPost(
      versionId,
      confirmationId,
      input,
    ),
    200,
  );
}
export async function judge(
  versionId: number,
  questionId: number,
  input: JudgementRequest,
) {
  return unwrapSuccess(
    await judgeApiV1UiVersionsVersionIdQuestionsQuestionIdJudgementsPost(
      versionId,
      questionId,
      input,
    ),
    201,
  );
}

export async function getInventory(versionId: number) {
  return unwrapSuccess(
    await getInventoryApiV1UiVersionsVersionIdInventoryGet(versionId),
    200,
  );
}

export async function listRecords(versionId: number) {
  return unwrapSuccess(
    await listRecordsApiV1UiVersionsVersionIdRecordsGet(versionId),
    200,
  );
}
export async function recordStateEvent(
  versionId: number,
  input: StateEventRequest,
) {
  return unwrapSuccess(
    await recordStateEventApiV1UiVersionsVersionIdStateEventsPost(
      versionId,
      input,
    ),
    201,
  );
}
export async function recordBounceComment(
  versionId: number,
  input: BounceCommentRequest,
) {
  return unwrapSuccess(
    await recordBounceCommentApiV1UiVersionsVersionIdBounceCommentsPost(
      versionId,
      input,
    ),
    201,
  );
}
export async function recordBounce(versionId: number, input: BounceRequest) {
  return unwrapSuccess(
    await recordBounceApiV1UiVersionsVersionIdBouncesPost(versionId, input),
    201,
  );
}
export async function recordSendoffDecision(
  versionId: number,
  input: SendoffDecisionRequest,
) {
  return unwrapSuccess(
    await recordSendoffDecisionApiV1UiVersionsVersionIdSendoffDecisionsPost(
      versionId,
      input,
    ),
    201,
  );
}

/** #38 出力。再送は別の出力を作るため、この関数は自動リトライしない。 */
export async function createExport(versionId: number) {
  const response =
    await createExportApiV1UiVersionsVersionIdExportsPost(versionId);
  if (response.status !== 200)
    throw new ApiError(response.status, { code: "E_UNEXPECTED_RESPONSE" });
  const headers = response.headers;
  const file = parseExportFileName(headers);
  return {
    blob: response.data,
    fileName: file.name,
    namedByServer: file.fromHeader,
  };
}
export async function listExports(versionId: number) {
  return unwrapSuccess(
    await listExportsApiV1UiVersionsVersionIdExportsGet(versionId),
    200,
  ).exports;
}
