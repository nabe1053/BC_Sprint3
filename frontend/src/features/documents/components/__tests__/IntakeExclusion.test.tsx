/**
 * F-16 RED: 資料投入画面のエラー強調・受付一覧の罫線・資料の除外（memory AD-036 ①）。
 * 除外は物理削除ではなく記録。除外者名は必須で AI は補完しない。
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/shared/api/mutator";
import { renderWithProviders } from "@/shared/testing/test-utils";

jest.mock("@/features/cases", () => ({
  CaseMetadata: () => <div data-testid="case-metadata" />,
}));
jest.mock("@/features/agent-runs", () => ({
  AgentRunPanel: () => <div data-testid="agent-run-panel" />,
}));
jest.mock("@/features/documents/hooks", () => ({
  useDocuments: jest.fn(),
  useIntakeDocument: jest.fn(),
  useExcludeDocument: jest.fn(),
  useDocumentExclusions: jest.fn(),
}));

import {
  useDocumentExclusions,
  useDocuments,
  useExcludeDocument,
  useIntakeDocument,
} from "@/features/documents/hooks";
import { IntakePage } from "@/features/documents/components/IntakePage";

const doc = {
  documentId: 7,
  fileName: "wrong.pdf",
  kind: "pdf",
  readStatus: "success",
  pageCount: 2,
  unreadableLocators: [],
};
const exclude = jest.fn();
const intake = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  exclude.mockResolvedValue({});
  (useDocuments as jest.Mock).mockReturnValue({
    data: [doc],
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  });
  (useIntakeDocument as jest.Mock).mockReturnValue({
    mutateAsync: intake,
    isPending: false,
  });
  (useExcludeDocument as jest.Mock).mockReturnValue({
    mutateAsync: exclude,
    isPending: false,
  });
  (useDocumentExclusions as jest.Mock).mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  });
});

it("投入のエラーは危険色の枠つき警告として目立たせ、原因の文言を残す", async () => {
  intake.mockRejectedValue(new ApiError(415, { code: "E_UNSUPPORTED_FORMAT" }));
  renderWithProviders(<IntakePage caseId={1} />);
  await userEvent.upload(
    screen.getByLabelText("ファイルを選択"),
    new File(["x"], "a.docx"),
  );
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveAttribute("data-tone", "danger");
  expect(alert).toHaveTextContent("未対応");
});

it("受付一覧の表は枠で囲み、列の区切り線を持つ", () => {
  renderWithProviders(<IntakePage caseId={1} />);
  const table = screen.getByRole("table", { name: "受付一覧" });
  // 外側の面（Paper）ではなく、表そのものの入れ物が枠を持つ。
  expect(table.parentElement).toHaveClass("MuiPaper-outlined");
});

it("除外は除外者名を必須にし、名前を入れると資料 ID と名前で記録する", async () => {
  renderWithProviders(<IntakePage caseId={1} />);
  await userEvent.click(
    screen.getByRole("button", { name: "wrong.pdf を除外" }),
  );
  const dialog = screen.getByRole("dialog", { name: /資料を除外/ });
  expect(dialog).toHaveTextContent("wrong.pdf");
  expect(dialog).toHaveTextContent("資料そのものは削除しません");
  const submit = within(dialog).getByRole("button", { name: "除外する" });
  await userEvent.click(submit);
  expect(exclude).not.toHaveBeenCalled();
  expect(within(dialog).getByLabelText(/除外者名/)).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await userEvent.type(within(dialog).getByLabelText(/除外者名/), " 担当 ");
  await userEvent.click(submit);
  expect(exclude).toHaveBeenCalledWith({ documentId: 7, recordedBy: "担当" });
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
});

it.each([
  ["E_RUN_IN_PROGRESS", 409, "案の作成中は除外できません"],
  ["E_ALREADY_EXCLUDED", 409, "既に除外されています"],
])("除外の失敗 %s は原因と直し方を示す", async (code, status, text) => {
  exclude.mockRejectedValue(new ApiError(status, { code }));
  renderWithProviders(<IntakePage caseId={1} />);
  await userEvent.click(
    screen.getByRole("button", { name: "wrong.pdf を除外" }),
  );
  const dialog = screen.getByRole("dialog");
  await userEvent.type(within(dialog).getByLabelText(/除外者名/), "担当");
  await userEvent.click(
    within(dialog).getByRole("button", { name: "除外する" }),
  );
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(text);
});

it("除外済みの資料は切替で表示し、除外者と日時（JST）を示す", async () => {
  (useDocumentExclusions as jest.Mock).mockReturnValue({
    data: [
      {
        documentId: 3,
        fileName: "old.xlsx",
        recordedBy: "担当",
        recordedAt: "2026-09-13T01:00:00Z",
      },
    ],
    isLoading: false,
    isError: false,
  });
  renderWithProviders(<IntakePage caseId={1} />);
  expect(screen.queryByText(/old\.xlsx/)).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "除外済みの資料を表示" }),
  );
  expect(useDocumentExclusions).toHaveBeenLastCalledWith(1, true);
  expect(
    screen.getByText("old.xlsx — 除外：担当 / 2026-09-13 10:00"),
  ).toBeInTheDocument();
});

it.each([
  [
    { data: [], isLoading: false, isError: false },
    "除外済みの資料はありません",
  ],
  [
    { data: undefined, isLoading: false, isError: true },
    "除外済みの資料を取得できませんでした",
  ],
])("除外済みの一覧は空・取得失敗を区別して示す（%#）", async (state, text) => {
  (useDocumentExclusions as jest.Mock).mockReturnValue(state);
  renderWithProviders(<IntakePage caseId={1} />);
  await userEvent.click(
    screen.getByRole("button", { name: "除外済みの資料を表示" }),
  );
  expect(screen.getByText(new RegExp(text))).toBeInTheDocument();
});

it("資料の投入中は除外ボタンを押せない", async () => {
  (useIntakeDocument as jest.Mock).mockReturnValue({
    mutateAsync: intake,
    isPending: true,
  });
  renderWithProviders(<IntakePage caseId={1} />);
  expect(
    screen.getByRole("button", { name: "wrong.pdf を除外" }),
  ).toBeDisabled();
});
