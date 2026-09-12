import {
  startRunApiV1UiCasesCaseIdAgentRunsPost,
  getRunApiV1UiAgentRunsRunIdGet,
  getStepsApiV1UiAgentRunsRunIdStepsGet,
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
