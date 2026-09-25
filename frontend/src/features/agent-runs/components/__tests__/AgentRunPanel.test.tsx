import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";
import type { AgentRunResponse } from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import {
  useStartAgentRun,
  useAgentRun,
  useAgentRunSteps,
  useActiveRun,
  useCarryOver,
} from "../../hooks";
import { AgentRunPanel } from "../AgentRunPanel";
jest.mock("../../hooks", () => ({
  useStartAgentRun: jest.fn(),
  useAgentRun: jest.fn(),
  useAgentRunSteps: jest.fn(),
  useActiveRun: jest.fn(),
  useCarryOver: jest.fn(),
}));
const start = jest.fn();
const progress = useAgentRun as jest.Mock;
const steps = useAgentRunSteps as jest.Mock;
const accepted = { runId: 3, versionId: 9, startedAt: "2026-09-12" };
const running: AgentRunResponse = {
  runId: 3,
  outcome: "running",
  stage: "reading",
  stageDetail: '{"documentsRead":1,"documentsTotal":3}',
  turns: 2,
  elapsedSec: 12,
  stopReason: null,
  versionId: null,
  isComplete: false,
  limits: {
    maxTurns: null,
    innerTimeoutS: null,
    inactivityTimeoutS: null,
    outerTimeoutS: null,
  },
};
function setRun(data: AgentRunResponse = running, error: Error | null = null) {
  progress.mockImplementation((id) =>
    id === null
      ? { data: undefined, isError: false }
      : { data, isError: !!error, error, isLoading: false },
  );
}
beforeEach(() => {
  jest.resetAllMocks();
  start.mockResolvedValue(accepted);
  (useStartAgentRun as jest.Mock).mockReturnValue({
    mutateAsync: start,
    isPending: false,
  });
  setRun();
  (useActiveRun as jest.Mock).mockReturnValue({ data: undefined });
  (useCarryOver as jest.Mock).mockReturnValue({
    data: [],
    isError: false,
    isLoading: false,
  });
  steps.mockReturnValue({
    data: [],
    isError: false,
    isLoading: false,
    refetch: jest.fn(),
  });
});
async function launch() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  return user;
}
it.each([
  "loading",
  "documentsError",
  "noReadable",
  "limitExceeded",
  "uploading",
] as const)("%sは理由を伴い起動不可", async (blockedReason) => {
  renderWithProviders(
    <AgentRunPanel caseId={8} blockedReason={blockedReason} />,
  );
  const button = screen.getByRole("button", { name: "案を作成" });
  expect(button).toBeDisabled();
  expect(button).toHaveAccessibleDescription();
  await userEvent.click(button, { pointerEventsCheck: 0 });
  expect(start).not.toHaveBeenCalled();
});
it("dblClickでもPOSTは1回、準備中は無効・受付版を結果にしない", async () => {
  let resolve!: (v: typeof accepted) => void;
  start.mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await userEvent.dblClick(screen.getByRole("button", { name: "案を作成" }));
  expect(start).toHaveBeenCalledTimes(1);
  expect(start).toHaveBeenCalledWith({ acknowledgedCarryOver: false });
  expect(screen.getByRole("button", { name: "準備中…" })).toBeDisabled();
  await act(async () => {
    resolve(accepted);
  });
  expect(screen.getByText("資料 1/3 を読取中")).toBeInTheDocument();
  expect(screen.getByText("経過 12 秒・2 ターン")).toBeInTheDocument();
  expect(screen.queryByText(/版番号/)).not.toBeInTheDocument();
});
it.each(["extracting", "self_checking"] as const)(
  "%sの段階を文字で表示",
  async (stage) => {
    setRun({ ...running, stage });
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    await launch();
    expect(
      screen.getByText(stage === "extracting" ? "明細を抽出中" : "自己点検中"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/資料 1\/3/)).not.toBeInTheDocument();
  },
);
it.each([
  '{"documentsRead":4,"documentsTotal":3}',
  '{"documentsRead":-1,"documentsTotal":3}',
  '{"documentsRead":1.5,"documentsTotal":3}',
  '{"documentsRead":"1","documentsTotal":3}',
  "null",
  "unknown_code",
  "<script>alert(1)</script>",
])("不正なstageDetail %sは露出しない", async (stageDetail) => {
  setRun({ ...running, stageDetail });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.getByText("資料を読取中")).toBeInTheDocument();
  expect(screen.queryByText(stageDetail)).not.toBeInTheDocument();
});
it.each([true, false])(
  "成功・isComplete=%sはGETで確定した版の確認リンクを表示",
  async (isComplete) => {
    setRun({
      ...running,
      outcome: "success",
      stage: "done",
      stopReason: "completed",
      versionId: 99,
      isComplete,
    });
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    await launch();
    expect(screen.getByText("案を作成しました")).toBeInTheDocument();
    // 内部の版 ID は画面に出さない（memory AD-036 ⑤）。版へはリンクで移る。
    expect(screen.queryByText(/版番号|99/)).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Item List を確認する" }),
    ).toBeInTheDocument();
    if (isComplete)
      expect(
        screen.queryByText("一部完了：確認が必要な箇所が残っています"),
      ).not.toBeInTheDocument();
    else
      expect(
        screen.getByText("一部完了：確認が必要な箇所が残っています"),
      ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Item List を確認する" }),
    ).toHaveAttribute("href", "/cases/8/versions/99");
  },
);
it.each([
  ["failed", "案の作成に失敗しました"],
  ["max_turns", "処理回数の上限で停止しました"],
  ["inner_timeout", "処理時間の上限で停止しました"],
  ["inactivity_timeout", "応答がないため停止しました"],
  ["outer_timeout", "ジョブの制限時間で停止しました"],
  ["repeated_call", "同じ処理の繰り返しを検知して停止しました"],
  ["no_readable_document", "読取可能な資料がないため停止しました"],
  ["validation_loop", "点検を解消できず停止しました"],
] as const)(
  "停止理由 %sを独立した文字ラベルで表示",
  async (stopReason, label) => {
    setRun({
      ...running,
      outcome: stopReason === "failed" ? "failed" : "stopped",
      stopReason,
      stage: "done",
      stageDetail: "worker_failed",
    });
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    await launch();
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(
      screen.getByText("処理中にエラーが発生しました"),
    ).toBeInTheDocument();
    expect(screen.queryByText("案を作成しました")).not.toBeInTheDocument();
  },
);
it.each([
  { outcome: "failed", stopReason: "completed", versionId: 99 },
  { outcome: "success", stopReason: "failed", versionId: 99 },
  { outcome: "success", stopReason: "completed", versionId: null },
  { outcome: "success", stopReason: "completed", versionId: 0 },
] as const)("不整合な終端%sを成功表示しない", async (terminal) => {
  setRun({ ...running, ...terminal, stage: "done" });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.queryByText("案を作成しました")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Item List を確認する" }),
  ).not.toBeInTheDocument();
});
it.each([404, 500])("GET %sのエラーは古いrunningより優先", async (status) => {
  setRun(running, new ApiError(status, { code: "E_NOT_FOUND" }));
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.getByRole("alert")).toHaveTextContent(
    status === 404 ? "実行が見つかりません" : "通信中断",
  );
  expect(screen.queryByText("資料 1/3 を読取中")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "案を作成" })).toBeDisabled();
});
it("引き継ぎ確認はチェック後の明示再操作のみ・件数を捏造しない", async () => {
  start.mockRejectedValueOnce(
    new ApiError(400, { code: "E_CARRY_OVER_NOT_ACKNOWLEDGED" }),
  );
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  const user = await launch();
  const check = screen.getByRole("checkbox", {
    name: "新版へ引き継がれないことを確認しました",
  });
  expect(check).not.toBeChecked();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "新版へは引き継がれません",
  );
  expect(screen.getByRole("alert")).not.toHaveTextContent(/\d+件/);
  expect(screen.getByRole("button", { name: "案を作成" })).toBeDisabled();
  await user.click(check);
  expect(start).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  expect(start).toHaveBeenCalledTimes(2);
  expect(start).toHaveBeenLastCalledWith({ acknowledgedCarryOver: true });
});
it.each([
  new TypeError("offline"),
  new ApiError(503, { code: "E_JOB_START_FAILED" }),
  new ApiError(202, { code: "E_UNEXPECTED_RESPONSE" }),
])("起動結果不明は状態を確認し直すまで再POST不可", async (error) => {
  start.mockRejectedValue(error);
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "起動結果を確認できません。状態を確認し直してから、必要なら再度起動してください",
  );
  expect(screen.getByRole("button", { name: "案を作成" })).toBeDisabled();
  await userEvent.dblClick(screen.getByRole("button", { name: "案を作成" }), {
    pointerEventsCheck: 0,
  });
  expect(start).toHaveBeenCalledTimes(1);
});
it.each([
  [409, "E_RUN_IN_PROGRESS", "別の実行が進行中です"],
  [503, "E_EXTERNAL_SEND_NOT_APPROVED", "外部送信が承認されていません"],
  [400, "E_NO_READABLE_DOCUMENT", "読取可能な資料がありません"],
  [413, "E_LIMIT_EXCEEDED", "入力上限を超えています"],
])("POST%s %sを表示し自動再送しない", async (status, code, label) => {
  start.mockRejectedValue(new ApiError(Number(status), { code: String(code) }));
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.getByRole("alert")).toHaveTextContent(String(label));
  expect(start).toHaveBeenCalledTimes(1);
});
it("steps補助の失敗は主進捗を壊さず、展開時だけ取得", async () => {
  steps.mockReturnValue({ isError: true, data: undefined, refetch: jest.fn() });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  const user = await launch();
  expect(steps).toHaveBeenLastCalledWith(3, false);
  await user.click(screen.getByRole("button", { name: "処理記録を表示" }));
  expect(steps).toHaveBeenLastCalledWith(3, true);
  expect(
    screen.getByText(
      "処理記録を取得できませんでした。再読み込みしてください。",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("資料 1/3 を読取中")).toBeInTheDocument();
});
it("stepsはseq順・生HTMLとリンクを実行しない", async () => {
  const row = {
    argsDigest: "hash",
    argsSummary: null,
    toolName: "read_document",
    documentId: 1,
    resultStatus: "ok",
    durationMs: 2,
    parentStepId: null,
  };
  steps.mockReturnValue({
    data: [
      {
        ...row,
        stepId: 2,
        seq: 2,
        locator: '<a href="https://example.com">unsafe</a>',
      },
      { ...row, stepId: 1, seq: 1, locator: "p.1" },
    ],
    isError: false,
  });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  const user = await launch();
  await user.click(screen.getByRole("button", { name: "処理記録を表示" }));
  const rows = within(
    screen.getByRole("list", { name: "処理記録" }),
  ).getAllByRole("listitem");
  expect(rows[0]).toHaveTextContent("p.1");
  // 内部のツール名・資料 ID・ms 表記は出さず、処理の名前と秒で示す（memory AD-036 ⑤）。
  expect(rows[0]).toHaveTextContent("資料を読取：正常");
  expect(rows[0]).toHaveTextContent("処理時間：0.1 秒未満");
  expect(rows[0]).not.toHaveTextContent("read_document");
  expect(rows[0]).not.toHaveTextContent("資料番号");
  expect(rows[0]).not.toHaveTextContent("資料：");
  expect(rows[1]).toHaveTextContent('<a href="https://example.com">unsafe</a>');
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
it("処理記録は資料をファイル名で示し、引数の要約・未知のツール名を出さない", async () => {
  steps.mockReturnValue({
    data: [
      {
        stepId: 1,
        seq: 1,
        argsDigest: "hash",
        argsSummary: "documentId=1 secret-args",
        toolName: "read_document",
        documentId: 1,
        locator: null,
        resultStatus: "ok",
        durationMs: 1234,
        parentStepId: null,
      },
      {
        stepId: 2,
        seq: 2,
        argsDigest: "hash",
        argsSummary: null,
        toolName: "job_interrupted",
        documentId: null,
        locator: null,
        resultStatus: "error",
        durationMs: null,
        parentStepId: null,
      },
      {
        stepId: 3,
        seq: 3,
        argsDigest: "hash",
        argsSummary: null,
        toolName: "unknown_tool_x",
        documentId: null,
        locator: null,
        resultStatus: "ok",
        durationMs: null,
        parentStepId: null,
      },
    ],
    isError: false,
  });
  renderWithProviders(
    <AgentRunPanel
      caseId={8}
      blockedReason={null}
      documentNames={new Map([[1, "sample-01.pdf"]])}
    />,
  );
  const user = await launch();
  await user.click(screen.getByRole("button", { name: "処理記録を表示" }));
  const rows = within(
    screen.getByRole("list", { name: "処理記録" }),
  ).getAllByRole("listitem");
  expect(rows[0]).toHaveTextContent("資料：sample-01.pdf");
  expect(rows[0]).toHaveTextContent("処理時間：1.2 秒");
  expect(rows[0]).not.toHaveTextContent("secret-args");
  expect(rows[1]).toHaveTextContent("実行の中断：エラー");
  expect(rows[2]).toHaveTextContent("その他の処理：正常");
  expect(rows[2]).not.toHaveTextContent("unknown_tool_x");
});
it("起動413の対象資料はファイル名で示す", async () => {
  start.mockRejectedValue(
    new ApiError(413, {
      code: "E_LIMIT_EXCEEDED",
      details: { kind: "pdfPages", actual: 201, limit: 200, documentId: 7 },
    }),
  );
  renderWithProviders(
    <AgentRunPanel
      caseId={8}
      blockedReason={null}
      documentNames={new Map([[7, "big.pdf"]])}
    />,
  );
  await launch();
  expect(screen.getByRole("alert")).toHaveTextContent("対象資料：big.pdf");
});
it.each([
  ["documents", "資料件数", "件", 51, 50],
  ["fileBytes", "ファイルサイズ", "バイト", 20971521, 20971520],
  ["pdfPages", "PDF のページ数", "ページ", 201, 200],
  ["xlsxSheets", "xlsx のシート数", "シート", 51, 50],
])(
  "起動413 %sは投入APIと別契約の単位で表示",
  async (kind, label, unit, actual, limit) => {
    start.mockRejectedValue(
      new ApiError(413, {
        code: "E_LIMIT_EXCEEDED",
        details: { kind, actual, limit, documentId: 7 },
      }),
    );
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    await launch();
    expect(screen.getByRole("alert")).toHaveTextContent(
      `${label}：${actual}${unit}（上限 ${limit}${unit}）`,
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent(/資料番号/);
  },
);
it("起動413の未知detailsは安全な上限案内を保持", async () => {
  start.mockRejectedValue(
    new ApiError(413, {
      code: "E_LIMIT_EXCEEDED",
      details: { kind: "unknown_kind", actual: 51, limit: 50 },
    }),
  );
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.getByRole("alert")).toHaveTextContent("入力上限を超えています");
  expect(screen.getByRole("alert")).not.toHaveTextContent("unknown_kind");
});
it("資料変更で引き継ぎチェックを解除し、明示確認をもう一度必要とする", async () => {
  start.mockRejectedValue(
    new ApiError(400, { code: "E_CARRY_OVER_NOT_ACKNOWLEDGED" }),
  );
  const { rerender } = renderWithProviders(
    <AgentRunPanel caseId={8} blockedReason={null} inputRevision="a" />,
  );
  const user = await launch();
  await user.click(screen.getByRole("checkbox"));
  expect(screen.getByRole("button", { name: "案を作成" })).toBeEnabled();
  rerender(<AgentRunPanel caseId={8} blockedReason={null} inputRevision="b" />);
  expect(screen.getByRole("checkbox")).not.toBeChecked();
  expect(screen.getByRole("button", { name: "案を作成" })).toBeDisabled();
  expect(start).toHaveBeenCalledTimes(1);
});
it("資料由来400は資料変更まで再POST不可、資料変更後は明示再操作できる", async () => {
  start.mockRejectedValueOnce(
    new ApiError(400, { code: "E_NO_READABLE_DOCUMENT" }),
  );
  const { rerender } = renderWithProviders(
    <AgentRunPanel caseId={8} blockedReason={null} inputRevision="a" />,
  );
  const user = await launch();
  expect(screen.getByRole("button", { name: "案を作成" })).toBeDisabled();
  rerender(<AgentRunPanel caseId={8} blockedReason={null} inputRevision="b" />);
  expect(start).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  expect(start).toHaveBeenCalledTimes(2);
});
it("模擬期の注記（実ファイルを抽出する処理ではありません）は出さない", async () => {
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  expect(
    screen.queryByText(/実ファイルを抽出する処理/),
  ).not.toBeInTheDocument();
  await launch();
  expect(
    screen.queryByText(/実ファイルを抽出する処理/),
  ).not.toBeInTheDocument();
});
it("実API相当のelapsedSec小数は切り捨てた秒で表示する", async () => {
  setRun({ ...running, elapsedSec: 12.3456789 });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.getByText("経過 12 秒・2 ターン")).toBeInTheDocument();
  expect(screen.queryByText(/12\.3456789/)).not.toBeInTheDocument();
});
it("done段階のrunningは結果を確定中であり完了ではない", async () => {
  setRun({ ...running, stage: "done" });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  await launch();
  expect(screen.getByText("結果を確定中")).toBeInTheDocument();
  expect(screen.queryByText("案を作成しました")).not.toBeInTheDocument();
});
it.each(["worker_failed", "trace_write_failed"])(
  "成功時には診断%sを併記しない",
  async (stageDetail) => {
    setRun({
      ...running,
      outcome: "success",
      stage: "done",
      stopReason: "completed",
      versionId: 99,
      isComplete: true,
      stageDetail,
    });
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    await launch();
    expect(screen.getByText("案を作成しました")).toBeInTheDocument();
    expect(
      screen.queryByText("処理中にエラーが発生しました"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("処理記録を保存できませんでした"),
    ).not.toBeInTheDocument();
  },
);
it.each([true, false])(
  "明示確認したrunの成功（isComplete=%s）で引き継ぎ結果を通知する",
  async (isComplete) => {
    const complete = {
      ...running,
      outcome: "success" as const,
      stage: "done" as const,
      stopReason: "completed" as const,
      versionId: 99,
      isComplete,
    };
    setRun(complete);
    start.mockRejectedValueOnce(
      new ApiError(400, { code: "E_CARRY_OVER_NOT_ACKNOWLEDGED" }),
    );
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    const user = await launch();
    const note =
      "前版の修正・確認記録は引き継がれていません（既存版は保全されています）";
    expect(screen.queryByText(note)).not.toBeInTheDocument();
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "案を作成" }));
    expect(start).toHaveBeenLastCalledWith({ acknowledgedCarryOver: true });
    expect(screen.getByText(note)).toBeInTheDocument();
    expect(screen.getByText(note)).not.toHaveTextContent(/\d+件/);
    // 次の、確認を伴わないrunへ通知を持ち越さない。
    await user.click(screen.getByRole("button", { name: "案を作成" }));
    expect(start).toHaveBeenLastCalledWith({ acknowledgedCarryOver: false });
    expect(screen.queryByText(note)).not.toBeInTheDocument();
  },
);
it("引き継ぎ確認済みでも失敗runには作成後通知を表示しない", async () => {
  setRun({
    ...running,
    outcome: "failed",
    stage: "done",
    stopReason: "failed",
  });
  start.mockRejectedValueOnce(
    new ApiError(400, { code: "E_CARRY_OVER_NOT_ACKNOWLEDGED" }),
  );
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  const user = await launch();
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  expect(screen.getByText("案の作成に失敗しました")).toBeInTheDocument();
  expect(
    screen.queryByText(
      "前版の修正・確認記録は引き継がれていません（既存版は保全されています）",
    ),
  ).not.toBeInTheDocument();
});
it("状態を確認し直す操作はPOSTせずbusyを解除、明示再起動の409を表示できる", async () => {
  const onBusyChange = jest.fn();
  start
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockRejectedValueOnce(new ApiError(409, { code: "E_RUN_IN_PROGRESS" }));
  renderWithProviders(
    <AgentRunPanel
      caseId={8}
      blockedReason={null}
      onBusyChange={onBusyChange}
    />,
  );
  const user = await launch();
  expect(onBusyChange).toHaveBeenLastCalledWith(true);
  await user.click(screen.getByRole("button", { name: "状態を確認し直す" }));
  expect(onBusyChange).toHaveBeenLastCalledWith(false);
  expect(start).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "案を作成" })).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  expect(start).toHaveBeenCalledTimes(2);
  expect(screen.getByRole("alert")).toHaveTextContent("別の実行が進行中です");
  expect(onBusyChange).toHaveBeenLastCalledWith(true);
  await user.click(screen.getByRole("button", { name: "状態を確認し直す" }));
  expect(start).toHaveBeenCalledTimes(2);
  expect(onBusyChange).toHaveBeenLastCalledWith(false);
});
it.each([404, 500])(
  "GET%sでも状態を確認し直すとエラーrunを解除し、再POSTしない",
  async (status) => {
    setRun(running, new ApiError(status, { code: "E_NOT_FOUND" }));
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    const user = await launch();
    await user.click(screen.getByRole("button", { name: "状態を確認し直す" }));
    expect(progress).toHaveBeenLastCalledWith(null);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "案を作成" })).toBeEnabled();
    expect(start).toHaveBeenCalledTimes(1);
  },
);

it("画面を開き直しても、案件の実行中runがあれば起動せずに進捗へ戻る（TEST-04 #1）", () => {
  (useActiveRun as jest.Mock).mockReturnValue({ data: { runId: 3 } });
  setRun({ ...running, stage: "extracting" });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  expect(start).not.toHaveBeenCalled();
  expect(progress).toHaveBeenLastCalledWith(3);
  expect(screen.getByText("明細を抽出中")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "準備中…" })).toBeDisabled();
});
it("実行中runが無ければ進捗を出さず起動できる", () => {
  (useActiveRun as jest.Mock).mockReturnValue({ data: { runId: null } });
  renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
  expect(progress).toHaveBeenLastCalledWith(null);
  expect(screen.getByRole("button", { name: "案を作成" })).toBeEnabled();
});
it.each([
  ["reading", ["実行中", "未着手", "未着手"]],
  ["extracting", ["完了", "実行中", "未着手"]],
  ["self_checking", ["完了", "完了", "実行中"]],
] as const)(
  "段階%sを3ステップの文字ラベルで示す（資料読取→抽出→自己点検）",
  async (stage, marks) => {
    setRun({ ...running, stage });
    renderWithProviders(<AgentRunPanel caseId={8} blockedReason={null} />);
    await launch();
    const list = screen.getByRole("list", { name: "処理の段階" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      `資料の読取：${marks[0]}`,
      `明細の抽出：${marks[1]}`,
      `自己点検：${marks[2]}`,
    ]);
  },
);

const carried = (changes: object = {}) => ({
  versionId: 44,
  versionNo: 2,
  editCount: 1,
  rowMatchConfirmed: 8,
  rowMatchTotal: 8,
  coverageRecorded: true,
  judgementCount: 0,
  ...changes,
});
it("記録のある既存版があれば、案作成ボタンの直前に件数つきの引き継ぎ警告を出す（TEST-16 #2）", () => {
  (useCarryOver as jest.Mock).mockReturnValue({
    data: [
      carried(),
      carried({
        versionId: 43,
        versionNo: 1,
        editCount: 0,
        rowMatchConfirmed: 0,
        coverageRecorded: false,
      }),
    ],
    isError: false,
    isLoading: false,
  });
  renderWithProviders(
    <AgentRunPanel caseId={40} blockedReason={null} showCarryOver />,
  );
  expect(useCarryOver).toHaveBeenCalledWith(40, true);
  const warning = screen.getByRole("region", { name: "記録の引き継ぎ警告" });
  expect(warning).toHaveTextContent(
    "v2：訂正 1件・照合 8/8行・網羅性確認 済・確認事項の判断 0件",
  );
  // 記録の無い版は数えない
  expect(warning).not.toHaveTextContent("v1：");
  expect(warning).toHaveTextContent("新版は作成案から始まり");
  expect(warning).toHaveTextContent("既存版は保全されます");
  // ボタンの直前に置く
  const button = screen.getByRole("button", { name: "案を作成" });
  expect(
    warning.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});
it("記録のある版が無い・指定の無い画面では引き継ぎ警告を出さない", () => {
  (useCarryOver as jest.Mock).mockReturnValue({
    data: [
      carried({ editCount: 0, rowMatchConfirmed: 0, coverageRecorded: false }),
    ],
    isError: false,
    isLoading: false,
  });
  const view = renderWithProviders(
    <AgentRunPanel caseId={40} blockedReason={null} showCarryOver />,
  );
  expect(
    screen.queryByRole("region", { name: "記録の引き継ぎ警告" }),
  ).not.toBeInTheDocument();
  view.unmount();
  (useCarryOver as jest.Mock).mockReturnValue({
    data: [carried()],
    isError: false,
    isLoading: false,
  });
  renderWithProviders(<AgentRunPanel caseId={40} blockedReason={null} />);
  expect(useCarryOver).toHaveBeenLastCalledWith(40, false);
  expect(
    screen.queryByRole("region", { name: "記録の引き継ぎ警告" }),
  ).not.toBeInTheDocument();
});
it("引き継ぎ件数を取得できなければ、件数を出さずに取得失敗と起動時の確認を示し再取得できる", async () => {
  (useCarryOver as jest.Mock).mockReturnValue({
    data: undefined,
    isError: true,
    isLoading: false,
  });
  const refetchCarryOver = jest.fn();
  (useCarryOver as jest.Mock).mockReturnValue({
    data: undefined,
    isError: true,
    isLoading: false,
    refetch: refetchCarryOver,
  });
  renderWithProviders(
    <AgentRunPanel caseId={40} blockedReason={null} showCarryOver />,
  );
  const alert = screen.getByRole("alert");
  expect(alert).toHaveTextContent(
    "既存版の記録件数を取得できませんでした。記録がある場合は、案の作成時に引き継がれないことの確認を求めます。",
  );
  await userEvent.click(within(alert).getByRole("button", { name: "再取得" }));
  expect(refetchCarryOver).toHaveBeenCalledTimes(1);
});
