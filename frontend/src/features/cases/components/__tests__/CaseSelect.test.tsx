/**
 * F-14 RED: SCR-03/05/06 の案件切替プルダウン（memory AD-036 ③）。
 * 案件を選ぶと、その案件の最新の確定版の同じ画面へ移る。版の無い案件は選べない。
 */
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "@/shared/testing/test-utils";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));
jest.mock("@/features/cases/hooks", () => ({ useCases: jest.fn() }));

import { useCases } from "@/features/cases/hooks";
import { CaseSelect } from "@/features/cases";

const row = (caseId: number, latestVersionId: number | null) => ({
  caseId,
  caseCode: `C${caseId}`,
  customerName: null,
  title: `案件${caseId}`,
  createdAt: "2026-09-01T00:00:00Z",
  progressStatus: latestVersionId ? "draft_review" : "intake",
  latestVersionId,
  latestSendoff: null,
  latestStateEvent: null,
  questionTotal: null,
  unresolvedCount: null,
});

beforeEach(() => {
  mockPush.mockReset();
  (useCases as jest.Mock).mockReturnValue({
    data: [row(1, 11), row(2, null), row(3, 33)],
    isLoading: false,
    isError: false,
  });
});

it("現在の案件を選択済みで示し、版の無い案件は選べない", () => {
  renderWithProviders(<CaseSelect caseId={1} target="items" />);
  const select = screen.getByLabelText("対象案件") as HTMLSelectElement;
  expect(select.value).toBe("1");
  const option = screen.getByRole("option", {
    name: /C2/,
  }) as HTMLOptionElement;
  expect(option.disabled).toBe(true);
  expect(option).toHaveTextContent("案がまだありません");
});

it.each([
  ["items", "/cases/3/versions/33"],
  ["inventory", "/cases/3/versions/33/inventory"],
  ["approval", "/cases/3/versions/33/approval"],
] as const)("%s で別案件を選ぶとその最新版の同じ画面へ移る", (target, href) => {
  renderWithProviders(<CaseSelect caseId={1} target={target} />);
  fireEvent.change(screen.getByLabelText("対象案件"), {
    target: { value: "3" },
  });
  expect(mockPush).toHaveBeenCalledWith(href);
});

it("取得中・失敗のときは選択欄を無効にし理由を示す", () => {
  (useCases as jest.Mock).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: true,
  });
  renderWithProviders(<CaseSelect caseId={1} target="items" />);
  expect(screen.getByLabelText("対象案件")).toBeDisabled();
  expect(
    screen.getByText(/案件一覧を取得できませんでした/),
  ).toBeInTheDocument();
});
