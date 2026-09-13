/**
 * T-103 RED: SCR-01 案件一覧（features/cases/components/CaseListPage.tsx）の失敗するテスト。
 *
 * 下位依存: features/cases/hooks.ts は mock する（実装しない）。
 * 期待する公開インタフェース:
 *   - export function CaseListPage(): JSX.Element  （"use client"）
 *
 * 検証観点（03-spec SCR-01 / design-guidelines / CLAUDE.md AD-008,009）:
 *   - 進捗ステータス: n/4 + 段階名がラベル文字として出る（色だけに頼らない）
 *   - 表示状態・送付可否: 版が無い案件では「—」
 *   - 3状態（空・ローディング・エラー）。エラーは原因と直し方を書く
 *   - 新規案件ダイアログ: caseCode 未入力で送信不可・重複時にその場でエラー
 *   - 「投入画面へ」導線がある
 */
import type { CaseResponse } from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import i18n from "@/shared/i18n";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

jest.mock("@/features/cases/hooks", () => ({
  useCases: jest.fn(),
  useCreateCase: jest.fn(),
}));

import { useCases, useCreateCase } from "@/features/cases/hooks";
import { CaseListPage } from "@/features/cases/components/CaseListPage";

const mockedUseCases = useCases as jest.Mock;
const mockedUseCreateCase = useCreateCase as jest.Mock;

const sampleCase = {
  caseId: 1,
  caseCode: "S04",
  customerName: "顧客A",
  title: "OCTG 引合",
  createdAt: "2026-09-01T00:00:00+09:00",
  progressStatus: "draft_review" as const,
  latestVersionId: 1,
  latestSendoff: null,
};

function setUseCases(overrides: Partial<ReturnType<typeof useCases>>) {
  mockedUseCases.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...overrides,
  });
}

function setUseCreateCase(
  overrides: Partial<ReturnType<typeof useCreateCase>> = {},
) {
  const mutateAsync = jest.fn().mockResolvedValue({ ...sampleCase, caseId: 8 });
  mockedUseCreateCase.mockReturnValue({
    mutateAsync,
    isPending: false,
    isError: false,
    error: null,
    ...overrides,
  });
  return mutateAsync;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("CaseListPage: 3状態", () => {
  it("ローディング中は明示的なローディング表示が出る", () => {
    setUseCases({ isLoading: true });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("空状態: 次の行動への誘導つきで表示する", () => {
    setUseCases({ data: [] });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    expect(screen.getByText("まだ案件がありません")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "最初の案件を作成しましょう" }),
    ).toBeInTheDocument();
  });

  it("エラー時は原因と直し方を書く（「エラーが発生しました」だけで終わらせない）", () => {
    setUseCases({
      isError: true,
      error: new ApiError(500, { message: "network" }),
    });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    expect(
      screen.getByText("案件一覧を読み込めませんでした"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("通信状況を確認し、再読み込みしてください"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/^エラーが発生しました$/),
    ).not.toBeInTheDocument();
  });
});

describe("CaseListPage: 進捗ステータス・表示状態・送付可否", () => {
  it("n/4 と段階名がラベル文字として表示される", () => {
    setUseCases({ data: [sampleCase] });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    expect(screen.getByText("2/4 案の確認")).toBeInTheDocument();
  });

  it("4段階メーターの各段階名がテキストとして存在する（色だけで判断しない）", () => {
    setUseCases({ data: [sampleCase] });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    for (const stage of [
      "資料投入",
      "案の確認",
      "担当者確認",
      "上司の評価確認",
    ]) {
      expect(screen.getAllByText(stage).length).toBeGreaterThan(0);
    }
  });

  it("AD-013: 進捗が案の確認でも表示状態・送付可否が「—」になる", () => {
    setUseCases({ data: [sampleCase] });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    const row = screen.getByText("S04").closest("tr") as HTMLElement;
    const dashes = within(row).getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("「投入画面へ」導線がある", () => {
    setUseCases({ data: [sampleCase] });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    expect(
      screen.getByRole("link", { name: i18n.t("cases.list.intakeLink") }),
    ).toHaveAttribute("href", "/cases/1/intake");
  });
});

describe("CaseListPage: 新規案件ダイアログ", () => {
  it("見出しに新規案件の投入画面ボタンがある", () => {
    setUseCases({ data: [] });
    setUseCreateCase();
    renderWithProviders(<CaseListPage />);
    expect(
      screen.getByRole("button", { name: "新規案件の投入画面" }),
    ).toBeInTheDocument();
  });

  it("caseCode 未入力では送信できない", async () => {
    const user = userEvent.setup();
    setUseCases({ data: [] });
    const mutateAsync = setUseCreateCase();
    renderWithProviders(<CaseListPage />);

    await user.click(
      screen.getByRole("button", { name: "新規案件の投入画面" }),
    );
    const submit = await screen.findByRole("button", { name: "作成する" });
    expect(submit).toBeDisabled();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("重複した照会番号はその場でエラー文言が出る", async () => {
    const user = userEvent.setup();
    setUseCases({ data: [] });
    setUseCreateCase({
      mutateAsync: jest.fn().mockRejectedValue(
        new ApiError(409, {
          code: "E_DUPLICATE_CASE_CODE",
          message: "duplicate",
        }),
      ),
    });
    renderWithProviders(<CaseListPage />);

    await user.click(
      screen.getByRole("button", { name: "新規案件の投入画面" }),
    );
    await user.type(await screen.findByLabelText("照会番号"), "S04");
    await user.click(screen.getByRole("button", { name: "作成する" }));

    await waitFor(() =>
      expect(
        screen.getByText("その照会番号はすでに使われています"),
      ).toBeInTheDocument(),
    );
  });
});

// 日本語直値は利用者に見える既定文言の契約を固定するために残す。追加のキーはi18n経由で検証。
it("版の状態と確認記録の案内を表示し案件を開ける", () => {
  setUseCases({ data: [sampleCase] });
  setUseCreateCase();
  renderWithProviders(<CaseListPage />);
  expect(screen.getByText(i18n.t("cases.list.versionNote"))).toHaveTextContent(
    "確認者・日時は承認画面で記録します",
  );
  expect(screen.getByText(i18n.t("cases.list.footnote"))).toHaveTextContent(
    "対外送付の承認ではありません",
  );
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getByRole("link", { name: "案件を開く" })).toHaveAttribute(
    "href",
    "/cases/1/versions/1",
  );
  expect(screen.getByText("作成案")).toBeInTheDocument();
});
it("作成した案件の投入画面へ進み、送信中の連打を防ぐ", async () => {
  const user = userEvent.setup();
  setUseCases({ data: [] });
  let resolve!: (value: CaseResponse) => void;
  const mutateAsync = jest.fn(
    () =>
      new Promise<CaseResponse>((r) => {
        resolve = r;
      }),
  );
  setUseCreateCase({ mutateAsync });
  renderWithProviders(<CaseListPage />);
  await user.click(screen.getByRole("button", { name: "新規案件の投入画面" }));
  await user.type(screen.getByLabelText("照会番号"), "NEW");
  const submit = screen.getByRole("button", { name: "作成する" });
  await user.dblClick(submit);
  expect(mutateAsync).toHaveBeenCalledTimes(1);
  expect(submit).toBeDisabled();
  resolve({ ...sampleCase, caseId: 8 });
  await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/cases/8/intake"));
});

it("最新版がnullなら案件を開くリンクを出さず投入画面へ案内する", () => {
  setUseCases({
    data: [{ ...sampleCase, latestVersionId: null, progressStatus: "intake" }],
  });
  setUseCreateCase();
  renderWithProviders(<CaseListPage />);
  expect(
    screen.queryByRole("link", { name: "案件を開く" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "投入画面へ" })).toHaveAttribute(
    "href",
    "/cases/1/intake",
  );
});

it.each([
  ["undecided", "未判断"],
  ["hold", "保留"],
  ["approved", "承認"],
  [null, "—"],
] as const)("G5送付可否%sを独立列に表示", (latestSendoff, label) => {
  setUseCases({ data: [{ ...sampleCase, latestSendoff }] });
  renderWithProviders(<CaseListPage />);
  const row = screen.getByRole("row", { name: /S04/ });
  expect(within(row).getAllByRole("cell")[4]).toHaveTextContent(label);
});
