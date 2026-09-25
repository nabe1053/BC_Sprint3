/**
 * F-12 RED: 画面左上の名称と、開発用の残骸表示（memory AD-036 ④⑤）。
 */
import { render, screen } from "@testing-library/react";
import "@/shared/i18n";
import { AppShell } from "../AppShell";

jest.mock("next/navigation", () => ({
  usePathname: () => "/cases",
}));

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
