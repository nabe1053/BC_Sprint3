import { EvidenceDrawer } from "../components/EvidenceDrawer";
import { ApprovalListsDrawer } from "../components/ApprovalListsDrawer";
import { fireEvent, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { ApiError } from "@/shared/api/mutator";
import * as hooks from "../hooks";
import { ApprovalPage } from "../components/ApprovalPage";
import { approvalData } from "../testing/fixtures";
import { useRouter } from "next/navigation";
jest.mock("../hooks");
jest.mock("next/navigation", () => ({ useRouter: jest.fn() }));
jest.mock("@/features/documents", () => ({
  useDocuments: () => ({
    data: [],
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  }),
}));
const mock = jest.mocked(hooks),
  push = jest.fn(),
  refetch = jest.fn();
const transition = jest.fn(),
  bounceComment = jest.fn(),
  bounce = jest.fn(),
  sendoff = jest.fn();
const query = (data: unknown) => ({
  data,
  isLoading: false,
  isError: false,
  isSuccess: true,
  error: null,
  refetch,
});
let data: ReturnType<typeof approvalData>;
function setup() {
  mock.useVersion.mockReturnValue(query(data.version) as never);
  mock.useItems.mockReturnValue(query(data.items) as never);
  mock.useQuestions.mockReturnValue(query(data.questions) as never);
  mock.useVersionHistory.mockReturnValue(query([data.listItem]) as never);
  mock.useRecords.mockReturnValue(query(data.records) as never);
}
beforeEach(() => {
  jest.resetAllMocks();
  data = approvalData();
  setup();
  jest.mocked(useRouter).mockReturnValue({ push } as never);
  for (const fn of [transition, bounceComment, bounce, sendoff])
    fn.mockResolvedValue({});
  mock.useApprovalMutations.mockReturnValue(
    Object.fromEntries(
      Object.entries({ transition, bounceComment, bounce, sendoff }).map(
        ([name, fn]) => [name, { mutateAsync: fn, isPending: false }],
      ),
    ) as never,
  );
  mock.useEvidence.mockReturnValue(query([]) as never);
});
const render = () =>
  renderWithProviders(<ApprovalPage caseId={8} versionId={9} />);
it.each([null, 4])(
  "索引%sの変更・判断事項に解決済み確認の理由と判断内容を併記",
  (itemId) => {
    data.questions = [
      {
        ...data.questions[0],
        reason: "規格の記載が二通り",
        latest: {
          ...data.questions[0].latest!,
          resolution: "resolved",
          note: "客先がL80を指定",
        },
      },
    ];
    renderWithProviders(
      <ApprovalListsDrawer
        items={data.items}
        questions={data.questions}
        itemId={itemId}
        onClose={jest.fn()}
        onAll={jest.fn()}
        onEvidence={jest.fn()}
      />,
    );
    const heading = screen.getByRole("heading", { name: /変更・判断事項（/ });
    const changes = within(heading.parentElement!);
    expect(
      changes.getByText("規格の記載が二通り / 客先がL80を指定"),
    ).toBeVisible();
    expect(
      within(screen.getByRole("dialog")).queryByRole("textbox"),
    ).not.toBeInTheDocument();
  },
);
it("h1・primaryは1つ、7要約・メタ・未解決注記・10列を表示する", () => {
  render();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(document.querySelectorAll(".MuiButton-contained")).toHaveLength(1);
  expect(screen.getAllByRole("columnheader")).toHaveLength(10);
  expect(screen.getByText("記録なし")).toBeVisible();
  expect(
    screen.getByText(/担当者：担当.*網羅性確認：網羅担当.*評価確認：未記録/),
  ).toBeVisible();
  expect(
    screen.getByText(/未解決 2 件を含めて評価確認を終えられます/),
  ).toBeVisible();
  expect(
    screen.getByText(
      "<b>https://example.test</b> — 上司 / 2026-09-13T01:00:00Z",
    ),
  ).toBeVisible();
  expect(document.querySelector('a[href="https://example.test"]')).toBeNull();
});
it.each(["draft", "review_checked"] as const)(
  "%sでは確認/差し戻しを無効にして理由を示す",
  (state) => {
    data.version.currentState = state;
    setup();
    render();
    expect(
      screen.getByRole("button", { name: "評価確認済みにする" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "差し戻す" })).toBeDisabled();
    expect(
      screen.getByText(
        state === "draft"
          ? /担当者の確認が未完了です（照合/
          : /評価確認済みです。訂正が記録されると/,
      ),
    ).toBeVisible();
  },
);
it("空名ではPOSTせず、記録後も留まり評価確認と送付の区別をstatus表示", async () => {
  render();
  fireEvent.click(screen.getByRole("button", { name: "評価確認済みにする" }));
  expect(transition).not.toHaveBeenCalled();
  expect(
    await screen.findByText("確認者名を入力してください。AI は補完しません。"),
  ).toBeVisible();
  fireEvent.change(screen.getByLabelText("確認者名（必須）"), {
    target: { value: " 評価者 " },
  });
  fireEvent.click(screen.getByRole("button", { name: "評価確認済みにする" }));
  await waitFor(() =>
    expect(transition).toHaveBeenCalledWith({
      toState: "review_checked",
      recordedBy: "評価者",
    }),
  );
  expect(
    await screen.findByText(
      "評価確認済みにしました（未解決 2 件を含む）。送付可否は別に判断してください。",
    ),
  ).toHaveAttribute("role", "status");
  expect(push).not.toHaveBeenCalled();
});
it("差し戻しの未紐付け0件はPOSTせず、成功時はItem Listへ戻る", async () => {
  data.records.unlinkedComments = [];
  setup();
  const view = render();
  fireEvent.change(screen.getByLabelText("確認者名（必須）"), {
    target: { value: "上司" },
  });
  fireEvent.click(screen.getByRole("button", { name: "差し戻す" }));
  expect(bounce).not.toHaveBeenCalled();
  expect(
    await screen.findByText(/差し戻す行にコメントを入力してください/),
  ).toBeVisible();
  data.records = approvalData().records;
  setup();
  view.rerender(<ApprovalPage caseId={8} versionId={9} />);
  fireEvent.click(screen.getByRole("button", { name: "差し戻す" }));
  await waitFor(() => expect(push).toHaveBeenCalledWith("/cases/8/versions/9"));
  expect(bounce).toHaveBeenCalledWith({ recordedBy: "上司" });
});
it("行コメントは明示記録だけ送信し、成功時だけ入力を空にする", async () => {
  render();
  fireEvent.change(screen.getByLabelText("確認者名（必須）"), {
    target: { value: "上司" },
  });
  const row = screen.getByRole("row", {
      name: "行 R1 の変更・判断事項と未解決事項を開く",
    }),
    input = within(row).getByLabelText("行 R1 の差し戻しコメント");
  fireEvent.click(within(row).getByRole("button", { name: "記録" }));
  expect(bounceComment).not.toHaveBeenCalled();
  await screen.findByText(
    "行コメントを入力してから記録してください。空のコメントは記録できません。",
  );
  expect(input).toHaveAttribute("aria-invalid", "true");
  fireEvent.change(input, { target: { value: " 原資料を確認 " } });
  fireEvent.blur(input);
  expect(bounceComment).not.toHaveBeenCalled();
  fireEvent.click(within(row).getByRole("button", { name: "記録" }));
  await waitFor(() =>
    expect(bounceComment).toHaveBeenCalledWith({
      itemId: 4,
      comment: "原資料を確認",
      recordedBy: "上司",
    }),
  );
  await waitFor(() => expect(input).toHaveValue(""));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
it("送付は判断者と保留理由を検査し未判断空理由をnullで送る", async () => {
  const user = userEvent.setup();
  render();
  const panel = screen.getByRole("region", { name: /② 送付可否/ });
  fireEvent.click(within(panel).getByRole("button", { name: "記録" }));
  expect(sendoff).not.toHaveBeenCalled();
  expect(
    await screen.findByText("判断者を入力してください。AI は補完しません。"),
  ).toBeVisible();
  fireEvent.change(screen.getByLabelText("判断者（必須）"), {
    target: { value: "判断者" },
  });
  await user.click(screen.getByRole("combobox", { name: "判断" }));
  await user.click(screen.getByRole("option", { name: "保留" }));
  fireEvent.click(within(panel).getByRole("button", { name: "記録" }));
  expect(sendoff).not.toHaveBeenCalled();
  expect(
    await screen.findByText(/保留・承認は理由・条件の入力が必要です/),
  ).toBeVisible();
  await user.click(screen.getByRole("combobox", { name: "判断" }));
  await user.click(screen.getByRole("option", { name: "未判断" }));
  fireEvent.click(within(panel).getByRole("button", { name: "記録" }));
  await waitFor(() =>
    expect(sendoff).toHaveBeenCalledWith({
      decision: "undecided",
      reason: null,
      recordedBy: "判断者",
    }),
  );
});
it("行の索引・全行索引・根拠は排他、閲覧専用には訂正/取消/判断フォームなし", async () => {
  render();
  fireEvent.keyDown(
    screen.getByRole("row", {
      name: "行 R1 の変更・判断事項と未解決事項を開く",
    }),
    { key: "Enter" },
  );
  const dialog = await screen.findByRole("dialog");
  expect(
    within(dialog).getByRole("heading", {
      name: "行 R1 の変更・判断事項と未解決事項",
    }),
  ).toBeVisible();
  expect(
    within(dialog).getByText(/行に紐づかない案件レベルの未解決 1 件/),
  ).toBeVisible();
  fireEvent.click(
    within(dialog).getByRole("button", { name: "この行の根拠を開く" }),
  );
  await waitFor(() => expect(screen.getAllByRole("dialog")).toHaveLength(1));
  expect(
    screen.queryByRole("button", { name: "訂正を記録" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "取消" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(
    within(screen.getByRole("dialog")).queryByRole("textbox"),
  ).not.toBeInTheDocument();
});
it("ボタン/入力上のclickやEnterは行索引を開かない", () => {
  render();
  const row = screen.getByRole("row", {
      name: "行 R1 の変更・判断事項と未解決事項を開く",
    }),
    input = within(row).getByRole("textbox");
  fireEvent.click(input);
  fireEvent.keyDown(input, { key: "Enter" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(within(row).getByRole("button", { name: "根拠" }));
  expect(screen.getByRole("dialog")).toHaveAccessibleName("行 R1 · Casing");
});
it.each(["table", "index"])(
  "%sから開いた根拠は前後行へ移動でき、両端だけ無効",
  async (entry) => {
    const user = userEvent.setup();
    render();
    if (entry === "index") {
      await user.click(screen.getByRole("combobox", { name: "表示" }));
      await user.click(screen.getByRole("option", { name: "訂正あり" }));
      fireEvent.click(
        screen.getByRole("row", {
          name: "行 R1 の変更・判断事項と未解決事項を開く",
        }),
      );
      fireEvent.click(
        screen.getByRole("button", { name: "この行の根拠を開く" }),
      );
    } else {
      const row = screen.getByRole("row", {
        name: "行 R1 の変更・判断事項と未解決事項を開く",
      });
      fireEvent.click(within(row).getByRole("button", { name: "根拠" }));
    }
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByRole("button", { name: "前の行" })).toBeDisabled();
    expect(dialog.getByRole("button", { name: "次の行" })).toBeEnabled();
    await user.click(dialog.getByRole("button", { name: "次の行" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("行 R2 · Casing");
    expect(mock.useEvidence).toHaveBeenLastCalledWith(9, 6);
    expect(dialog.getByRole("button", { name: "次の行" })).toBeDisabled();
    expect(dialog.getByRole("button", { name: "前の行" })).toBeEnabled();
    expect(dialog.queryByRole("textbox")).not.toBeInTheDocument();
    expect(dialog.queryByRole("checkbox")).not.toBeInTheDocument();
    await user.click(dialog.getByRole("button", { name: "前の行" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("行 R1 · Casing");
    expect(mock.useEvidence).toHaveBeenLastCalledWith(9, 4);
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
  },
);
it("空/読込/404/取得失敗/版一覧に該当なしを明示する", () => {
  mock.useVersion.mockReturnValue({
    ...query(undefined),
    isLoading: true,
  } as never);
  const view = render();
  expect(screen.getByText("読み込み中...")).toBeVisible();
  mock.useVersion.mockReturnValue({
    ...query(undefined),
    isError: true,
    error: new ApiError(404, { code: "E_NOT_FOUND" }),
  } as never);
  view.rerender(<ApprovalPage caseId={8} versionId={9} />);
  expect(
    screen.getByText(
      "版が見つかりません。案件一覧から版を選び直してください。",
    ),
  ).toBeVisible();
  setup();
  mock.useVersionHistory.mockReturnValue(query([]) as never);
  view.rerender(<ApprovalPage caseId={8} versionId={9} />);
  expect(
    screen.getByText(
      "承認データを取得できませんでした。接続を確認して再取得してください。",
    ),
  ).toBeVisible();
  data.items = [];
  setup();
  view.rerender(<ApprovalPage caseId={8} versionId={9} />);
  expect(screen.getByText(/この版に明細がありません/)).toBeVisible();
  expect(
    screen.getByRole("button", { name: /変更・判断事項 0 行/ }),
  ).toBeVisible();
});
it("409の表示は行IDと網羅性だけ、内部ID・生本文を出さない", async () => {
  transition.mockRejectedValue(
    new ApiError(409, {
      code: "E_STAFF_CHECK_INCOMPLETE",
      message: "private-message",
      details: {
        unmatchedItemIds: [98765],
        unmatchedRowCodes: ["R1"],
        coverageRecorded: false,
      },
    }),
  );
  render();
  fireEvent.change(screen.getByLabelText("確認者名（必須）"), {
    target: { value: "人" },
  });
  fireEvent.click(screen.getByRole("button", { name: "評価確認済みにする" }));
  expect(await screen.findByText(/未照合 1 行（R1）/)).toBeVisible();
  expect(document.body).not.toHaveTextContent("98765");
  expect(document.body).not.toHaveTextContent("private-message");
});

it("readOnlyは操作コールバックが渡されても訂正・取消・判断・照合を出さない", () => {
  renderWithProviders(
    <EvidenceDrawer
      readOnly
      caseId={8}
      versionId={9}
      item={data.items[0]}
      questions={data.questions}
      recordedBy="人"
      previous={null}
      next={null}
      onClose={jest.fn()}
      onMove={jest.fn()}
      onMatch={jest.fn()}
      onEdit={jest.fn()}
      onUndo={jest.fn()}
      onJudge={jest.fn()}
      onReload={jest.fn()}
    />,
  );
  const dialog = screen.getByRole("dialog");
  expect(within(dialog).queryByRole("textbox")).not.toBeInTheDocument();
  expect(within(dialog).queryByRole("checkbox")).not.toBeInTheDocument();
  expect(
    within(dialog).queryByRole("button", { name: "取消" }),
  ).not.toBeInTheDocument();
  expect(within(dialog).getByText("客先回答待ち")).toBeVisible();
});
it.each([
  "全行",
  "変更・判断事項のある行",
  "訂正あり",
  "未解決のみ",
  "差し戻しコメントあり",
])("絞り込み%sでも索引の全体件数は変わらない", async (name) => {
  const user = userEvent.setup();
  render();
  await user.click(screen.getByRole("combobox", { name: "表示" }));
  await user.click(screen.getByRole("option", { name }));
  expect(
    screen.getByText(name === "全行" ? "2 / 2 行" : "1 / 2 行"),
  ).toBeVisible();
  expect(
    screen.getByRole("button", {
      name: "変更・判断事項 1 行 ／ 未解決 2 件 を開く",
    }),
  ).toBeVisible();
});
it("API導出の差し戻し中・再確認と現在の送付判断を表示する", () => {
  data.listItem.bounced = true;
  data.listItem.needsRecheck = true;
  data.listItem.latestSendoff = {
    sendoffDecisionId: 1,
    decision: "hold",
    reason: "回答待ち",
    recordedBy: "判断者",
    recordedAt: "2026-09-13T01:00:00Z",
  };
  setup();
  render();
  expect(screen.getByText("差し戻し中（作成案には戻りません）")).toBeVisible();
  expect(screen.getByText(/再確認が必要（評価確認済みの後に/)).toBeVisible();
  expect(
    screen.getByText("現在：保留 ／ 判断者 ／ 2026-09-13T01:00:00Z"),
  ).toBeVisible();
});
it("空名で評価確認を押すと確認者名の欄そのものをエラーにして理由を示す（TEST-14 #1）", async () => {
  render();
  fireEvent.click(screen.getByRole("button", { name: "評価確認済みにする" }));
  expect(transition).not.toHaveBeenCalled();
  const field = screen.getByLabelText("確認者名（必須）");
  await waitFor(() =>
    expect(field).toHaveAccessibleDescription(
      "確認者名を入力してください。入力するまで評価確認・差し戻し・行コメントは記録されません。AI は補完しません。",
    ),
  );
  expect(field.closest(".MuiInputBase-root")).toHaveClass("Mui-error");
  fireEvent.change(field, { target: { value: "評価者" } });
  expect(field.closest(".MuiInputBase-root")).not.toHaveClass("Mui-error");
});
