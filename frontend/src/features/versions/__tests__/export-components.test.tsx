import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { ApiError } from "@/shared/api/mutator";
import * as hooks from "../hooks";
import { ExportButton } from "../components/ExportButton";
import { VersionHistory } from "../components/VersionHistory";
import { approvalData } from "../testing/fixtures";
jest.mock("../hooks");
jest.mock("@/features/agent-runs", () => ({
  AgentRunPanel: () => <div data-testid="agent-run-panel" />,
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
const exportRecord = {
  exportId: 1,
  fileName: "S-01__v2_draft.xlsx",
  storagePath: "1/uuid.xlsx",
  contentHash: "abc",
  exportedAt: "2026-09-13T09:00:00+09:00",
  stateAtExport: "draft",
  sendoffAtExport: null,
  unresolvedAtExport: 2,
  isInitial: true,
  integrity: "intact",
};
const mutateAsync = jest.fn();
beforeEach(() => {
  jest.clearAllMocks();
  mock.useCreateExport.mockReturnValue({
    mutateAsync,
    isPending: false,
  } as never);
});

describe("ExportButton", () => {
  it("押すと出力しファイル名を知らせる", async () => {
    const click = jest.spyOn(HTMLAnchorElement.prototype, "click");
    global.URL.createObjectURL = jest.fn(() => "blob:x");
    global.URL.revokeObjectURL = jest.fn();
    mutateAsync.mockResolvedValue({
      blob: new Blob(["x"]),
      exportId: "1",
      fileName: "S-01__v2_draft.xlsx",
      namedByServer: true,
    });
    renderWithProviders(<ExportButton versionId={9} label="出力" />);
    await userEvent.click(screen.getByRole("button", { name: "出力" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mock.useCreateExport).toHaveBeenCalledWith(9);
    expect(click).toHaveBeenCalled();
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith("blob:x");
    expect(
      await screen.findByText(/S-01__v2_draft\.xlsx を保存しました/),
    ).toBeInTheDocument();
    click.mockRestore();
  });
  it("disabled prop が渡れば無効になる（未生成の実経路は TODO-044）", () => {
    renderWithProviders(
      <ExportButton versionId={9} label="出力" disabled={true} />,
    );
    expect(screen.getByRole("button", { name: "出力" })).toBeDisabled();
  });
  it("出力中は無効化して二重出力を防ぐ", () => {
    mock.useCreateExport.mockReturnValue({
      mutateAsync,
      isPending: true,
    } as never);
    renderWithProviders(<ExportButton versionId={9} label="出力" />);
    const button = screen.getByRole("button", { name: "出力中…" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });
  it.each([
    [409, "E_VERSION_NOT_FINALIZED", /まだ確定していません/],
    [404, "E_NOT_FOUND", /版は見つかりません/],
  ])("失敗は原因と直し方を出す（%s）", async (status, code, text) => {
    mutateAsync.mockRejectedValue(new ApiError(status as number, { code }));
    renderWithProviders(<ExportButton versionId={9} label="出力" />);
    await userEvent.click(screen.getByRole("button", { name: "出力" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(text);
  });
});

describe("VersionHistory", () => {
  function setup(listItem = approvalData().listItem) {
    mock.useVersionHistory.mockReturnValue(query([listItem]) as never);
    mock.useExports.mockReturnValue(query([exportRecord]) as never);
    renderWithProviders(<VersionHistory caseId={8} versionId={9} />);
  }
  it("版ごとに 作成日時・生成所要・状態・未解決・出力ボタン を出す", () => {
    setup();
    expect(screen.getByText(/生成所要: 631.5 秒/)).toBeInTheDocument();
    expect(screen.getByText("未解決 2 件")).toBeInTheDocument();
    expect(screen.getByText("出力時の未解決: 2")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "版 1 を出力" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/AI の待ち時間は人の作業時間に含めません/),
    ).toBeInTheDocument();
  });
  it("生成所要が未記録なら「未記録」と出す（0秒と区別）", () => {
    setup({ ...approvalData().listItem, elapsedSec: null });
    expect(screen.getByText(/生成所要: 未記録/)).toBeInTheDocument();
  });
  it("出力履歴は保全状態をラベル文字で出す", () => {
    setup();
    expect(
      screen.getByText(/ファイル名: S-01__v2_draft\.xlsx/),
    ).toBeInTheDocument();
    expect(screen.getByText(/^作成日時: /)).toBeInTheDocument();
    expect(screen.getByText("状態: 担当者確認済み")).toBeInTheDocument();
    expect(
      screen.getByText(/保存ファイルの状態: 保存どおり/),
    ).toBeInTheDocument();
    expect(screen.getByText("初回の出力")).toBeInTheDocument();
  });
  it("再実行・引き継ぎ警告・出力シートの説明・写しの注記・比較枠を出す", () => {
    setup();
    expect(screen.getByTestId("agent-run-panel")).toBeInTheDocument();
    expect(screen.getByText(/新版へ引き継がれません/)).toBeInTheDocument();
    expect(screen.getByText(/5シートです/)).toBeInTheDocument();
    expect(
      screen.getByText(/正式メーカー書式ではありません/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/編集内容はアプリに取り込まれません/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2 版を比較" })).toBeDisabled();
  });
  it("未生成のときは案作成への誘導を出す", () => {
    mock.useVersionHistory.mockReturnValue(query([]) as never);
    mock.useExports.mockReturnValue(query([]) as never);
    renderWithProviders(<VersionHistory caseId={8} versionId={9} />);
    expect(
      screen.getByText(/未生成。資料投入画面で案を作成/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("この版はまだ出力していません。"),
    ).toBeInTheDocument();
  });
  it("未解決があれば「含めて出力する」旨と、出力時の評価状態・送付可否を併記する", () => {
    setup();
    expect(
      screen.getByText(/未解決 2 件を含めて出力します/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /評価状態「担当者確認済み」・送付可否「未判断」として書き出されます/,
      ),
    ).toBeInTheDocument();
  });
  it("出力履歴の読取失敗は出力失敗と別の文言を出す", () => {
    mock.useVersionHistory.mockReturnValue(
      query([approvalData().listItem]) as never,
    );
    mock.useExports.mockReturnValue({
      ...query(undefined),
      isError: true,
      isSuccess: false,
    } as never);
    renderWithProviders(<VersionHistory caseId={8} versionId={9} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "出力履歴を取得できませんでした",
    );
  });
  it("版一覧の読取失敗は原因と再読込を出す", () => {
    mock.useVersionHistory.mockReturnValue({
      ...query(undefined),
      isError: true,
      isSuccess: false,
    } as never);
    mock.useExports.mockReturnValue(query([]) as never);
    renderWithProviders(<VersionHistory caseId={8} versionId={9} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
