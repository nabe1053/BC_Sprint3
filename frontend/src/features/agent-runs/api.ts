import {
  startRunApiV1UiCasesCaseIdAgentRunsPost,
  getRunApiV1UiAgentRunsRunIdGet,
  getStepsApiV1UiAgentRunsRunIdStepsGet,
  getActiveRunApiV1UiCasesCaseIdAgentRunsActiveGet,
  listVersionsApiV1UiCasesCaseIdVersionsGet,
} from "@/shared/api/generated/ui";
import type { AgentRunRequest } from "@/shared/api/generated/model";
import { unwrapSuccess } from "@/shared/api/unwrap";
import { ApiError } from "@/shared/api/mutator";

export async function startAgentRun(
  caseId: number,
  input: AgentRunRequest = {},
) {
  const accepted = unwrapSuccess(
    await startRunApiV1UiCasesCaseIdAgentRunsPost(caseId, input),
    202,
  );
  if (!Number.isSafeInteger(accepted.runId) || accepted.runId <= 0) {
    throw new ApiError(202, { code: "E_UNEXPECTED_RESPONSE" });
  }
  return accepted;
}
export async function getAgentRun(runId: number, signal?: AbortSignal) {
  const run = unwrapSuccess(
    await getRunApiV1UiAgentRunsRunIdGet(runId, { signal }),
    200,
  );
  if (run.runId !== runId)
    throw new ApiError(200, { code: "E_UNEXPECTED_RESPONSE" });
  return run;
}
export async function getAgentRunSteps(runId: number, signal?: AbortSignal) {
  return unwrapSuccess(
    await getStepsApiV1UiAgentRunsRunIdStepsGet(runId, { signal }),
    200,
  ).steps;
}
/** 画面に戻ったときの復帰先（F-17）: 実行中の run と、終了済みを含む直近の run。 */
export async function getRunResume(caseId: number, signal?: AbortSignal) {
  const { runId, latestRunId } = unwrapSuccess(
    await getActiveRunApiV1UiCasesCaseIdAgentRunsActiveGet(caseId, { signal }),
    200,
  );
  const valid = (id: number | null) =>
    id === null || (Number.isSafeInteger(id) && id > 0);
  if (!valid(runId) || !valid(latestRunId))
    throw new ApiError(200, { code: "E_UNEXPECTED_RESPONSE" });
  return { runId, latestRunId };
}
// 案作成ボタン直前の引き継ぎ警告の材料。版一覧 #22 の carryOver（未取消の記録件数）を使う。
export async function listCarryOver(caseId: number, signal?: AbortSignal) {
  return unwrapSuccess(
    await listVersionsApiV1UiCasesCaseIdVersionsGet(caseId, { signal }),
    200,
  ).versions.map(({ versionId, versionNo, carryOver }) => ({
    versionId,
    versionNo,
    ...carryOver,
  }));
}
