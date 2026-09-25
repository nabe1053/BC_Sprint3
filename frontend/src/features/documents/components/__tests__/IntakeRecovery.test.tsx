import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { IntakePage } from "../IntakePage";

jest.mock("@/features/cases", () => ({ CaseMetadata: () => null }));
jest.mock("../../hooks", () => ({
  useDocuments: () => ({
    data: [
      {
        documentId: 1,
        fileName: "input.txt",
        kind: "text",
        readStatus: "success",
        pageCount: 1,
        unreadableLocators: [],
      },
    ],
  }),
  useIntakeDocument: () => ({ isPending: false }),
}));
const originalFetch = global.fetch;
const request = jest.fn();
beforeEach(() => {
  request.mockReset();
  // 画面表示時の「実行中runの確認」と「引き継ぎ警告の版一覧」は固定で答え、
  // 起動・進捗の通信列だけを request で数える。
  global.fetch = ((input: RequestInfo | URL, init?: RequestInit) =>
    /\/agent-runs\/active$/.test(String(input))
      ? Promise.resolve(response(200, { runId: null }))
      : /\/cases\/\d+\/versions$/.test(String(input))
        ? Promise.resolve(response(200, { versions: [] }))
        : request(input, init)) as typeof fetch;
});
afterAll(() => {
  global.fetch = originalFetch;
});
function response(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => body,
  };
}
it("実生成クライアント: POST通信失敗→状態リセットは通信0→明示再起動409でも資料投入の復帰経路がある", async () => {
  const user = userEvent.setup();
  request
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(response(409, { code: "E_RUN_IN_PROGRESS" }));
  renderWithProviders(<IntakePage caseId={8} />);
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  await screen.findByText(
    "起動結果を確認できません。状態を確認し直してから、必要なら再度起動してください",
  );
  expect(screen.getByLabelText("ファイルを選択")).toBeDisabled();
  expect(request).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "状態を確認し直す" }));
  await waitFor(() =>
    expect(screen.getByLabelText("ファイルを選択")).toBeEnabled(),
  );
  expect(request).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "案を作成" })).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  await screen.findByText(/別の実行が進行中です/);
  expect(request).toHaveBeenCalledTimes(2);
  expect(request.mock.calls.every(([, init]) => init.method === "POST")).toBe(
    true,
  );
  expect(screen.getByLabelText("ファイルを選択")).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "状態を確認し直す" }));
  expect(request).toHaveBeenCalledTimes(2);
  await waitFor(() =>
    expect(screen.getByLabelText("ファイルを選択")).toBeEnabled(),
  );
});
it("実HTTP400→明示確認POST202→GET200の成功で引き継ぎ通知と整数秒を表示", async () => {
  const user = userEvent.setup();
  request
    .mockResolvedValueOnce(
      response(400, { code: "E_CARRY_OVER_NOT_ACKNOWLEDGED" }),
    )
    .mockResolvedValueOnce(
      response(202, { runId: 3, versionId: 9, startedAt: "2026-09-12" }),
    )
    .mockResolvedValueOnce(
      response(200, {
        runId: 3,
        outcome: "success",
        stage: "done",
        stageDetail: "trace_write_failed",
        turns: 2,
        elapsedSec: 12.3456789,
        stopReason: "completed",
        versionId: 99,
        isComplete: true,
        limits: {
          maxTurns: null,
          innerTimeoutS: null,
          inactivityTimeoutS: null,
          outerTimeoutS: null,
        },
      }),
    );
  renderWithProviders(<IntakePage caseId={8} />);
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  await user.click(await screen.findByRole("checkbox"));
  expect(request).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "案を作成" }));
  await screen.findByText(
    "前版の修正・確認記録は引き継がれていません（既存版は保全されています）",
  );
  expect(
    screen.getByRole("link", { name: "Item List を確認する" }),
  ).toHaveAttribute("href", "/cases/8/versions/99");
  expect(screen.getByText("経過 12 秒・2 ターン")).toBeInTheDocument();
  expect(
    screen.queryByText("処理記録を保存できませんでした"),
  ).not.toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(3);
  expect(JSON.parse(request.mock.calls[1][1].body)).toEqual({
    acknowledgedCarryOver: true,
  });
  expect(request.mock.calls[2][1].method).toBe("GET");
});
it("資料投入画面は記録のある既存版の件数を案作成ボタンの直前に示す（TEST-16 #2）", async () => {
  global.fetch = ((input: RequestInfo | URL) =>
    Promise.resolve(
      /\/agent-runs\/active$/.test(String(input))
        ? response(200, { runId: null })
        : response(200, {
            versions: [
              {
                versionId: 44,
                versionNo: 2,
                currentState: "staff_checked",
                finalizedAt: "2026-09-24T21:41:29Z",
                isComplete: true,
                createdAt: "2026-09-24T21:37:12Z",
                unresolvedCount: 0,
                carryOver: {
                  editCount: 1,
                  rowMatchConfirmed: 8,
                  rowMatchTotal: 8,
                  coverageRecorded: true,
                  judgementCount: 0,
                },
                latestStateEvent: null,
                latestBounce: null,
                latestSendoff: null,
                bounced: false,
                needsRecheck: false,
                elapsedSec: null,
              },
            ],
          }),
    )) as typeof fetch;
  renderWithProviders(<IntakePage caseId={40} />);
  const warning = await screen.findByRole("region", {
    name: "記録の引き継ぎ警告",
  });
  expect(warning).toHaveTextContent(
    "v2：訂正 1件・照合 8/8行・網羅性確認 済・確認事項の判断 0件",
  );
});
