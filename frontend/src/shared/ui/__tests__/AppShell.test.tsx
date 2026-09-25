/**
 * F-12 RED: 画面左上の名称と、開発用の残骸表示（memory AD-036 ④⑤）。
 */
import { render, screen } from "@testing-library/react";
import "@/shared/i18n";
import { AppShell } from "../AppShell";

const mockPath = { current: "/cases" };
jest.mock("next/navigation", () => ({
  usePathname: () => mockPath.current,
}));
beforeEach(() => {
  mockPath.current = "/cases";
  try {
    window.sessionStorage.clear();
  } catch {
    // ignore
  }
});

it("左上に「引合書整理エージェント」を表示し、SPRINT 3 の副題は出さない", () => {
  render(<AppShell>body</AppShell>);
  expect(screen.getByText("引合書整理エージェント")).toBeInTheDocument();
  expect(screen.queryByText(/SPRINT 3/)).not.toBeInTheDocument();
  expect(screen.queryByText(/OCTG/)).not.toBeInTheDocument();
});

it("設計書への言及を含むフッターを出さない", () => {
  render(<AppShell>body</AppShell>);
  expect(screen.queryByText(/03-spec/)).not.toBeInTheDocument();
  expect(document.querySelector("footer")).toBeNull();
});

// ---- F-14: 左ナビは版が URL に無くても案件の最新版で開ける（memory AD-036 ③） ----
const latest = (caseId: number) => (caseId === 5 ? 9 : null);

it("資料投入画面（版なしの URL）でも案件の最新版で 03〜05 を開ける", () => {
  mockPath.current = "/cases/5/intake";
  render(<AppShell latestVersionOf={latest}>body</AppShell>);
  expect(
    screen.getByRole("link", { name: "03 Item List 確認" }),
  ).toHaveAttribute("href", "/cases/5/versions/9");
  expect(screen.getByRole("link", { name: "04 網羅性照合" })).toHaveAttribute(
    "href",
    "/cases/5/versions/9/inventory",
  );
  expect(screen.getByRole("link", { name: "05 引合書承認" })).toHaveAttribute(
    "href",
    "/cases/5/versions/9/approval",
  );
});

it("案件一覧に戻っても直前に開いた案件でナビを開ける", () => {
  mockPath.current = "/cases/5/intake";
  const { unmount } = render(
    <AppShell latestVersionOf={latest}>body</AppShell>,
  );
  unmount();
  mockPath.current = "/cases";
  render(<AppShell latestVersionOf={latest}>body</AppShell>);
  expect(
    screen.getByRole("link", { name: "02 資料投入・読取結果" }),
  ).toHaveAttribute("href", "/cases/5/intake");
  expect(
    screen.getByRole("link", { name: "03 Item List 確認" }),
  ).toHaveAttribute("href", "/cases/5/versions/9");
});

it("版がまだ無い案件では 03〜05 を無効のまま理由を示す", () => {
  mockPath.current = "/cases/7/intake";
  render(<AppShell latestVersionOf={latest}>body</AppShell>);
  expect(
    screen.queryByRole("link", { name: "03 Item List 確認" }),
  ).not.toBeInTheDocument();
  expect(screen.getAllByTitle("案を作成すると開けます")).toHaveLength(3);
});

it("URL の版を優先する（古い版を開いているときは最新版へ飛ばさない）", () => {
  mockPath.current = "/cases/5/versions/4/inventory";
  render(<AppShell latestVersionOf={latest}>body</AppShell>);
  expect(
    screen.getByRole("link", { name: "03 Item List 確認" }),
  ).toHaveAttribute("href", "/cases/5/versions/4");
});
