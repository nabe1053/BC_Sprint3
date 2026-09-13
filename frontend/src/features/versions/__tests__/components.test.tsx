import { fireEvent, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { DimensionValue } from "../components/ItemValue";
import { VersionHistory } from "../components/VersionHistory";
import { ItemListPage } from "../components/ItemListPage";
import * as hooks from "../hooks";
import i18n from "@/shared/i18n";
import { ApiError } from "@/shared/api/mutator";
import { useRouter } from "next/navigation";
jest.mock("next/navigation", () => ({ useRouter: jest.fn() }));
const approvalPush = jest.fn(),
  staffTransition = jest.fn();
import {
  approvalData,
  item,
  edit,
  question,
  version,
} from "../testing/fixtures";
jest.mock("../hooks");
jest.mock("@/features/documents", () => ({
  useDocuments: () => ({
    data: [{ documentId: 1, fileName: "<b>https://private.test</b>" }],
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  }),
}));
const mock = jest.mocked(hooks);
const refetch = jest.fn();
const query = (data: unknown) => ({
  data,
  isLoading: false,
  isError: false,
  isSuccess: true,
  error: null,
  refetch,
});
const mutate = jest.fn();
const mutation = { mutateAsync: mutate, isPending: false, error: null };
beforeEach(() => {
  jest.resetAllMocks();
  mutate.mockResolvedValue({});
  staffTransition.mockResolvedValue({});
  jest.mocked(useRouter).mockReturnValue({ push: approvalPush } as never);
  mock.useApprovalMutations.mockReturnValue({
    transition: { mutateAsync: staffTransition, isPending: false },
  } as never);
  mock.useVersion.mockReturnValue(query(version) as never);
  mock.useItems.mockReturnValue(
    query([
      item,
      {
        ...item,
        itemId: 7,
        rowCode: "R2",
        seq: 2,
        qtyState: "numeric",
        qtyValue: "9007199254740993.0010",
        qtyUnit: "本",
        groupCode: "G1",
        history: [
          { ...edit, itemId: 7 },
          { ...edit, itemId: 7, editId: 3, field: "qty_unit", oldValue: "m" },
        ],
      },
    ]) as never,
  );
  mock.useQuestions.mockReturnValue(
    query([
      question,
      {
        ...question,
        questionId: 6,
        questionCode: "Q2",
        itemId: null,
        reason: "期限のTZを確認",
        latest: {
          judgementId: 7,
          questionId: 6,
          status: "judged",
          resolution: "unresolved",
          note: "照会",
          recordedBy: "担当",
          recordedAt: edit.recordedAt,
        },
      },
    ]) as never,
  );
  mock.useVersionHistory.mockReturnValue(
    query([
      {
        versionId: 9,
        versionNo: 1,
        currentState: "draft",
        isComplete: false,
        finalizedAt: version.finalizedAt,
        unresolvedCount: 0,
        elapsedSec: null,
      },
    ]) as never,
  );
  mock.useEvidence.mockReturnValue(
    query([
      {
        evidenceId: 1,
        field: "grade",
        rawValue: "K55",
        adoptedValue: "K55",
        documentId: 1,
        locator: "body:1",
        quote: "<script>https://private.test</script>",
        appliedCondition: "共通条件",
        conversionNote: "換算なし",
        changeReason: "改訂",
        priorValue: "J55",
      },
    ]) as never,
  );
  // T-603: 版の履歴に出力履歴・出力ボタンが載る。
  mock.useExports.mockReturnValue(query([]) as never);
  mock.useCreateExport.mockReturnValue({
    mutateAsync: jest.fn(),
    isPending: false,
  } as never);
  mock.useRecordMutations.mockReturnValue({
    edit: mutation,
    undoEdit: mutation,
    confirm: mutation,
    undoConfirmation: mutation,
    judge: mutation,
  } as never);
});
const render = () =>
  renderWithProviders(<ItemListPage caseId={8} versionId={9} />);
it("明細・7件数・版の状態・TBA・択一・旧値を文字で示し合計は出さない", () => {
  render();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getByText("数量未確定")).toBeVisible();
  expect(screen.getByText("択一")).toBeVisible();
  expect(screen.getAllByText("TBA", { selector: "span" })).toHaveLength(2);
  expect(screen.getByText("9007199254740993.0010")).toBeVisible();
  expect(screen.getByText("訂正 · 旧 10.00")).toBeVisible();
  expect(screen.getByText("訂正 · 旧 m")).toBeVisible();
  for (const label of [
    "明細",
    "確認事項のある行",
    "数量TBA",
    "択一グループ",
    "照合済み",
    "訂正",
    "未解決の確認事項",
  ])
    expect(screen.getAllByText(label).length).toBeGreaterThan(0);
  expect(screen.getByText("1 / 2")).toBeVisible();
  expect(screen.getByText("訂正のある明細 1 行")).toBeVisible();
  expect(screen.queryByText(/合計数量/)).not.toBeInTheDocument();
  expect(document.querySelectorAll(".MuiButton-contained")).toHaveLength(1);
});
it("loadingと404には原因・戻り先、明細空には専用表示がある", () => {
  mock.useVersion.mockReturnValue({
    ...query(undefined),
    isLoading: true,
  } as never);
  const view = render();
  expect(screen.getByRole("status")).toHaveTextContent("読み込み");
  mock.useVersion.mockReturnValue({
    ...query(undefined),
    isLoading: false,
    isError: true,
    error: new ApiError(404, { code: "E_NOT_FOUND", message: "private" }),
  } as never);
  view.rerender(<ItemListPage caseId={8} versionId={9} />);
  expect(screen.getByText("版が見つかりません")).toBeVisible();
  expect(screen.getByRole("link", { name: "案件一覧へ" })).toHaveAttribute(
    "href",
    "/cases",
  );
  expect(screen.queryByText("private")).not.toBeInTheDocument();
  mock.useVersion.mockReturnValue(query(version) as never);
  mock.useItems.mockReturnValue(query([]) as never);
  view.rerender(<ItemListPage caseId={8} versionId={9} />);
  expect(screen.getByText("この版に明細がありません")).toBeVisible();
});
it("絞り込み0件からクリアし、判断済み未解決は案件枠に残る", async () => {
  render();
  fireEvent.change(screen.getByLabelText("キーワード"), {
    target: { value: "no-such-row" },
  });
  expect(screen.getByText(/条件に一致する明細はありません/)).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "条件をクリア" }));
  expect(screen.getByText("R1")).toBeVisible();
  const section = screen.getByRole("region", {
    name: "案件レベルの確認事項（案件）",
  });
  expect(within(section).getByText("期限のTZを確認")).toBeVisible();
  expect(within(section).getByLabelText("対応状況")).toHaveValue("judged");
  expect(within(section).getByLabelText("解決状態")).toHaveValue("unresolved");
});
it("担当者名空では照合を変えずPOSTしない、名前を入れると明示記録する", async () => {
  render();
  const checkbox = screen.getByRole("checkbox", {
    name: "行 R1 の重要項目を出典と照合した",
  });
  await userEvent.click(checkbox);
  expect(checkbox).not.toBeChecked();
  expect(mutate).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toHaveTextContent("記録者名を入力");
  fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
    target: { value: " 担当 " },
  });
  await userEvent.click(checkbox);
  expect(mutate).toHaveBeenCalledWith({
    kind: "row_match",
    itemId: 4,
    recordedBy: "担当",
  });
});
it("判断selectを変えただけではPOSTせず行の記録ボタンで送る", async () => {
  render();
  fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
    target: { value: "担当" },
  });
  const form = screen.getByRole("form", { name: "確認事項 Q1" });
  fireEvent.change(within(form).getByLabelText("対応状況"), {
    target: { value: "judged" },
  });
  expect(mutate).not.toHaveBeenCalled();
  await userEvent.click(within(form).getByRole("button", { name: "記録" }));
  expect(mutate).toHaveBeenCalledWith({
    questionId: 5,
    status: "judged",
    resolution: "unresolved",
    note: null,
    recordedBy: "担当",
  });
});
it("ドロワーは絞り込み後の順に前後移動し、根拠のHTMLとURLは文字列", async () => {
  render();
  await userEvent.click(
    screen.getAllByRole("button", { name: "詳細を見る" })[0],
  );
  const drawer = screen.getByRole("dialog");
  expect(
    within(drawer).getByRole("heading", { name: "行 R1 · Casing", level: 2 }),
  ).toBeVisible();
  expect(within(drawer).getByRole("button", { name: "前の行" })).toBeDisabled();
  expect(
    within(drawer).getByText("<script>https://private.test</script>"),
  ).toBeVisible();
  expect(within(drawer).getByText("<b>https://private.test</b>")).toBeVisible();
  expect(within(drawer).queryByRole("link")).not.toBeInTheDocument();
  expect(drawer.querySelector("script")).toBeNull();
  await userEvent.click(within(drawer).getByRole("button", { name: "次の行" }));
  expect(
    within(drawer).getByRole("heading", { name: "行 R2 · Casing" }),
  ).toBeVisible();
  expect(within(drawer).getByRole("button", { name: "次の行" })).toBeDisabled();
});
it("訂正の理由が空なら送信せず、状態のみ訂正は値を載せず記録する", async () => {
  render();
  fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
    target: { value: "担当" },
  });
  await userEvent.click(
    screen.getAllByRole("button", { name: "詳細を見る" })[0],
  );
  const drawer = screen.getByRole("dialog");
  await userEvent.click(
    within(drawer).getByRole("button", { name: "訂正を記録" }),
  );
  expect(mutate).not.toHaveBeenCalled();
  expect(within(drawer).getByRole("alert")).toHaveTextContent("修正理由を入力");
  fireEvent.change(within(drawer).getByLabelText("対象項目"), {
    target: { value: "qty_value" },
  });
  fireEvent.change(within(drawer).getByLabelText("値の状態"), {
    target: { value: "tba" },
  });
  fireEvent.change(within(drawer).getByLabelText("修正理由（必須）"), {
    target: { value: "照合" },
  });
  await userEvent.click(
    within(drawer).getByRole("button", { name: "訂正を記録" }),
  );
  expect(mutate).toHaveBeenCalledWith({
    itemId: 4,
    field: "qty_value",
    newState: "tba",
    reason: "照合",
    recordedBy: "担当",
  });
});
it.each([
  "E_REASON_REQUIRED",
  "E_RECORDER_REQUIRED",
  "E_QTY_UNIT_REQUIRED",
  "E_STATE_VALUE_CONFLICT",
  "E_TARGET_INVALID",
  "E_REQUEST_INVALID",
  "E_FIELD_NOT_EDITABLE",
  "E_ALREADY_UNDONE",
  "E_ALREADY_CONFIRMED",
  "E_NOT_FOUND",
  "E_INTERNAL",
])("記録失敗 %s は生のmessage/detailsを出さない", async (code) => {
  mutate.mockRejectedValue(
    new ApiError(code === "E_INTERNAL" ? 500 : 400, {
      code,
      message: "sensitive-value",
      details: { input: "sensitive-value" },
    }),
  );
  render();
  fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
    target: { value: "担当" },
  });
  await userEvent.click(
    screen.getByRole("checkbox", { name: "行 R1 の重要項目を出典と照合した" }),
  );
  await waitFor(() => expect(screen.getByRole("alert")).toBeVisible());
  expect(screen.getByRole("alert")).not.toHaveTextContent("sensitive-value");
  expect(screen.getByRole("alert")).not.toHaveTextContent(code);
  expect(screen.getByRole("alert")).toHaveTextContent(
    i18n.t(
      code === "E_INTERNAL"
        ? "versions.errors.unknown"
        : `versions.errors.${code}`,
    ),
  );
  expect(mutate).toHaveBeenCalledTimes(1);
});

it("照合取消は応答のconfirmationIdを送り、訂正取消後も履歴を表示する", async () => {
  const matched = {
    ...item,
    history: [edit],
    rowMatch: {
      confirmationId: 33,
      recordedBy: "照合者",
      recordedAt: edit.recordedAt,
    },
  };
  mock.useItems.mockReturnValue(query([matched]) as never);
  const view = render();
  fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
    target: { value: "取消者" },
  });
  const checkbox = screen.getByRole("checkbox", {
    name: "行 R1 の重要項目を出典と照合した",
  });
  expect(checkbox).toBeChecked();
  await userEvent.click(checkbox);
  expect(mutate).toHaveBeenCalledWith({
    confirmationId: 33,
    recordedBy: "取消者",
  });
  await userEvent.click(screen.getByRole("button", { name: "詳細を見る" }));
  await userEvent.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "取り消す",
    }),
  );
  expect(mutate).toHaveBeenLastCalledWith({ editId: 2, recordedBy: "取消者" });
  mock.useItems.mockReturnValue(
    query([
      {
        ...matched,
        rowMatch: null,
        history: [
          { ...edit, undoneAt: "2026-09-13T02:00:00Z", undoneBy: "取消者" },
        ],
      },
    ]) as never,
  );
  view.rerender(<ItemListPage caseId={8} versionId={9} />);
  const drawer = screen.getByRole("dialog");
  expect(within(drawer).getByText("取消済み")).toBeVisible();
  expect(
    within(drawer).getByText("取消者 / 2026-09-13T02:00:00Z"),
  ).toBeVisible();
  expect(
    within(drawer).queryByRole("button", { name: "取り消す" }),
  ).not.toBeInTheDocument();
  expect(within(drawer).getByRole("checkbox")).not.toBeChecked();
});
it("絞り込みで残った1行のドロワーは両端が無効で根拠空を区別する", async () => {
  mock.useEvidence.mockReturnValue(query([]) as never);
  mock.useQuestions.mockReturnValue(query([]) as never);
  render();
  fireEvent.change(screen.getByLabelText("キーワード"), {
    target: { value: "R2" },
  });
  await userEvent.click(screen.getByRole("button", { name: "詳細を見る" }));
  const drawer = screen.getByRole("dialog");
  expect(within(drawer).getByRole("button", { name: "前の行" })).toBeDisabled();
  expect(within(drawer).getByRole("button", { name: "次の行" })).toBeDisabled();
  expect(
    within(drawer).getByText("この行の根拠は登録されていません"),
  ).toBeVisible();
  expect(
    within(drawer).getByText(
      "確認事項はありません。原資料との照合は必要です。",
    ),
  ).toBeVisible();
});
it("案件ヘッダは原表記・粒度・基準とTZ不足を示す", () => {
  mock.useVersion.mockReturnValue(
    query({
      ...version,
      caseHeader: {
        inquiryNoState: "not_stated",
        customerNameState: "stated",
        customerName: "顧客",
        dueState: "stated",
        dueRaw: "Q4",
        dueGranularity: "quarter",
        dueBasis: "arrival",
        placeRaw: null,
        placeState: "not_applicable",
        incoterms: "FOB",
        incotermsState: "stated",
        quoteDeadlineRaw: "Friday COB",
        quoteDeadlineTzState: "missing",
      },
    }) as never,
  );
  render();
  expect(screen.getByText("Q4")).toBeVisible();
  expect(screen.getByText("四半期 / 到着")).toBeVisible();
  expect(screen.getByText("Friday COB")).toBeVisible();
  expect(screen.getByText("タイムゾーンの記載がありません")).toBeVisible();
});
it.each(["useItems", "useQuestions"] as const)(
  "%sの取得失敗は再取得できる",
  async (name) => {
    mock[name].mockReturnValue({
      ...query(undefined),
      isError: true,
      error: new Error("private"),
    } as never);
    render();
    expect(screen.getByRole("alert")).toHaveTextContent("接続を確認して再取得");
    await userEvent.click(screen.getByRole("button", { name: "再取得" }));
    expect(refetch).toHaveBeenCalled();
    expect(screen.queryByText("private")).not.toBeInTheDocument();
  },
);
it("SCR-03の見出し右に出力ボタンが1つあり、primaryは増やさない（03-spec:178）", () => {
  render();
  const header = screen.getByRole("banner");
  expect(
    within(header).getByRole("button", { name: "現在の記録を出力" }),
  ).toBeEnabled();
  // primary（塗り）は「担当者確認済みにする」の1つのまま。
  expect(document.querySelectorAll(".MuiButton-contained")).toHaveLength(1);
});
it("版履歴部品は空と取得失敗を区別する", async () => {
  mock.useVersionHistory.mockReturnValue(query([]) as never);
  const view = renderWithProviders(<VersionHistory caseId={8} versionId={9} />);
  expect(
    screen.getByText("未生成。資料投入画面で案を作成してください"),
  ).toBeInTheDocument();
  mock.useVersionHistory.mockReturnValue({
    ...query(undefined),
    isError: true,
    error: new Error("private"),
  } as never);
  view.rerender(<VersionHistory caseId={8} versionId={9} />);
  expect(screen.getByRole("alert", { hidden: true })).toHaveTextContent(
    "接続を確認して再取得",
  );
});

it("ドロワーでは納期・納地の採用値も状態と根拠を確認できるが編集対象にしない", async () => {
  mock.useItems.mockReturnValue(
    query([
      {
        ...item,
        dueRaw: "Q4",
        dueState: "stated",
        placeRaw: null,
        placeState: "not_applicable",
      },
    ]) as never,
  );
  render();
  await userEvent.click(screen.getByRole("button", { name: "詳細を見る" }));
  const drawer = screen.getByRole("dialog");
  expect(within(drawer).getByRole("heading", { name: "納期" })).toBeVisible();
  expect(within(drawer).getByRole("heading", { name: "納地" })).toBeVisible();
  expect(
    within(drawer).getByText("適用なし", { selector: "span" }),
  ).toBeVisible();
  expect(
    within(drawer)
      .getByLabelText("対象項目")
      .querySelector('option[value="due_raw"]'),
  ).toBeNull();
  expect(
    within(drawer)
      .getByLabelText("対象項目")
      .querySelector('option[value="place_raw"]'),
  ).toBeNull();
});

it("レンジと定尺長は共有状態でも併記し状態ラベルは1つにする", () => {
  mock.useItems.mockReturnValue(
    query([
      {
        ...item,
        rangeClass: "R3",
        lengthValue: null,
        lengthUnit: null,
        lengthState: "not_stated",
      },
    ]) as never,
  );
  render();
  const cell = screen.getByText("レンジ R3／定尺長 —").closest("td")!;
  expect(within(cell).getAllByText("記載なし")).toHaveLength(1);
});

it.each(["od", "weight", "wall"] as const)(
  "%s の値と単位が共有する状態はセルに1回だけ表示する",
  (dimension) => {
    const row = {
      ...item,
      [`${dimension}State`]: "not_stated",
      [`${dimension}Value`]: null,
      [`${dimension}Unit`]: null,
    };
    renderWithProviders(
      <table>
        <tbody>
          <tr>
            <td>
              <DimensionValue item={row} dimension={dimension} />
            </td>
          </tr>
        </tbody>
      </table>,
    );
    expect(
      within(screen.getByRole("cell")).getAllByText("記載なし"),
    ).toHaveLength(1);
  },
);
it.each([
  ["od", 3],
  ["weight", 4],
] as const)("一覧の%s列に記載なしを重複表示しない", (dimension, index) => {
  mock.useItems.mockReturnValue(
    query([{ ...item, [`${dimension}State`]: "not_stated" }]) as never,
  );
  render();
  const row = screen.getByRole("rowheader", { name: "R1" }).closest("tr")!;
  expect(
    within(row.children[index] as HTMLElement).getAllByText("記載なし"),
  ).toHaveLength(1);
});

it.each([true, false])(
  "網羅性照合への導線は確認済み=%sでも常に表示",
  (coverageConfirmed) => {
    mock.useVersion.mockReturnValue(
      query({ ...version, coverageConfirmed }) as never,
    );
    render();
    expect(screen.getByRole("link", { name: "網羅性照合へ" })).toHaveAttribute(
      "href",
      "/cases/8/versions/9/inventory",
    );
  },
);

it("G5担当者確認は空名を拒否しstaff_checkedを1回記録して承認へ進む", async () => {
  render();
  fireEvent.click(screen.getByRole("button", { name: "担当者確認済みにする" }));
  expect(staffTransition).not.toHaveBeenCalled();
  await screen.findByText("確認者名を入力してください。AI は補完しません。");
  expect(screen.getByLabelText("担当者名（記録に共用）")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
    target: { value: " 担当者 " },
  });
  fireEvent.click(screen.getByRole("button", { name: "担当者確認済みにする" }));
  await waitFor(() =>
    expect(staffTransition).toHaveBeenCalledWith({
      toState: "staff_checked",
      recordedBy: "担当者",
    }),
  );
  expect(approvalPush).toHaveBeenCalledWith("/cases/8/versions/9/approval");
});
it("G5担当者確認の不足は行ID・網羅性と照合画面へのリンクを表示", async () => {
  staffTransition.mockRejectedValue(
    new ApiError(409, {
      code: "E_STAFF_CHECK_INCOMPLETE",
      details: {
        unmatchedItemIds: [98765],
        unmatchedRowCodes: ["R1"],
        coverageRecorded: false,
      },
    }),
  );
  render();
  fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
    target: { value: "担当者" },
  });
  fireEvent.click(screen.getByRole("button", { name: "担当者確認済みにする" }));
  expect(
    await screen.findByText(/未照合 1 行（R1）。網羅性確認/),
  ).toBeVisible();
  expect(
    screen
      .getAllByRole("link", { name: "網羅性照合へ" })
      .some(
        (link) => link.getAttribute("href") === "/cases/8/versions/9/inventory",
      ),
  ).toBe(true);
  expect(document.body).not.toHaveTextContent("98765");
});
it("G5差し戻し中・再確認はAPIのラベルと理由だけを表示、primaryは0", () => {
  const d = approvalData();
  mock.useVersion.mockReturnValue(
    query({ ...version, currentState: "staff_checked" }) as never,
  );
  mock.useVersionHistory.mockReturnValue(
    query([
      {
        ...d.listItem,
        bounced: true,
        needsRecheck: true,
        latestBounce: {
          bounceId: 1,
          reason: "R1: <b>原資料</b>\nR2: 再確認",
          recordedBy: "上司",
          recordedAt: edit.recordedAt,
          comments: [],
        },
      },
    ]) as never,
  );
  render();
  expect(document.querySelectorAll(".MuiButton-contained")).toHaveLength(0);
  expect(screen.getByRole("link", { name: "引合書承認へ" })).toHaveAttribute(
    "href",
    "/cases/8/versions/9/approval",
  );
  expect(screen.getByText("差し戻し中（作成案には戻りません）")).toBeVisible();
  expect(screen.getByText(/再確認が必要：評価確認済みの後に/)).toBeVisible();
  expect(screen.getByText("R1: <b>原資料</b>").tagName).toBe("BLOCKQUOTE");
  expect(mock.useRecords).not.toHaveBeenCalled();
});

it("G5版一覧に現在版が無い場合は取得失敗として操作を出さない", () => {
  mock.useVersionHistory.mockReturnValue(query([]) as never);
  render();
  expect(screen.getByRole("alert")).toHaveTextContent("接続を確認して再取得");
  expect(
    screen.queryByRole("button", { name: "担当者確認済みにする" }),
  ).not.toBeInTheDocument();
});
