import { unwrapSuccess } from "@/shared/api/unwrap";
import {
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
} from "@/shared/api/generated/ui";
import type {
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
