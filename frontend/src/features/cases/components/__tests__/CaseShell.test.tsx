/**
 * F-14: 左ナビに案件の最新版を渡し、画面を移るたびに案件一覧を取り直す（RV-057 P2）。
 */
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/shared/testing/test-utils";
import "@/shared/i18n";

const mockPath = { current: "/cases/5/intake" };
jest.mock("next/navigation", () => ({ usePathname: () => mockPath.current }));
jest.mock("@/features/cases/hooks", () => ({ useCases: jest.fn() }));

import { useCases } from "@/features/cases/hooks";
import { CaseShell } from "@/features/cases";

const refetch = jest.fn();
beforeEach(() => {
  refetch.mockReset();
  mockPath.current = "/cases/5/intake";
  (useCases as jest.Mock).mockReturnValue({
    data: [{ caseId: 5, latestVersionId: 9 }],
    isLoading: false,
    isError: false,
    refetch,
  });
});

it("案件一覧の最新版で左ナビの 03 を開ける", () => {
  renderWithProviders(<CaseShell>body</CaseShell>);
  expect(
    screen.getByRole("link", { name: "03 Item List 確認" }),
  ).toHaveAttribute("href", "/cases/5/versions/9");
});

it("画面（パス）が変わったら案件一覧を取り直す", () => {
  const { rerender } = renderWithProviders(<CaseShell>body</CaseShell>);
  const before = refetch.mock.calls.length;
  mockPath.current = "/cases/5/versions/9";
  rerender(<CaseShell>body</CaseShell>);
  expect(refetch.mock.calls.length).toBe(before + 1);
});

it("案件一覧の取得中は「案を作成すると開けます」と誤って示さない", () => {
  (useCases as jest.Mock).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    refetch,
  });
  renderWithProviders(<CaseShell>body</CaseShell>);
  expect(screen.queryByTitle("案を作成すると開けます")).not.toBeInTheDocument();
  expect(screen.getAllByTitle("案件の情報を読み込み中です")).toHaveLength(3);
});
