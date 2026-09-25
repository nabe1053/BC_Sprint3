import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/shared/api/mutator";
import { muiColor } from "@/shared/theme/mui-color";
import { tokens } from "@/shared/theme/tokens";
import { Providers } from "../providers";
import { CaseListPage } from "@/features/cases";
import { IntakePage } from "@/features/documents";

jest.mock("@mui/material-nextjs/v15-appRouter", () => ({
  AppRouterCacheProvider: ({ children }: { children: ReactNode }) => children,
}));
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));
jest.mock("@/features/cases/hooks", () => ({
  useCases: () => ({
    data: [
      {
        caseId: 1,
        caseCode: "THEME",
        progressStatus: "intake",
        title: null,
        customerName: null,
      },
    ],
  }),
  useCreateCase: () => ({}),
  useCase: () => ({
    data: { caseCode: "THEME", title: null, customerName: null },
  }),
}));
jest.mock("@/features/documents/hooks", () => ({
  useDocuments: () => ({
    data: [
      {
        documentId: 1,
        fileName: "theme.txt",
        kind: "text",
        readStatus: "partial",
        pageCount: 4,
        unreadableLocators: ["p.2"],
      },
    ],
  }),
  useIntakeDocument: () => ({ mutateAsync: mockIntake, isPending: false }),
  useExcludeDocument: () => ({ mutateAsync: jest.fn(), isPending: false }),
  useDocumentExclusions: () => ({ data: [], isLoading: false, isError: false }),
}));
const mockIntake = jest.fn();
it.each(["cases", "intake"])(
  "本番テーマで%sの表を描画できる（color-mixも維持）",
  (view) => {
    render(
      <Providers>
        {view === "cases" ? <CaseListPage /> : <IntakePage caseId={1} />}
      </Providers>,
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  },
);

it("MUI用変換は罫線トークンの元の色と透明度を保つ", () => {
  expect(muiColor(tokens.colors.divider)).toBe("rgba(29, 31, 32, 0.16)");
  expect(muiColor(tokens.colors.accent)).toBe(tokens.colors.accent);
});

// F-16（実ブラウザで発覚）: MUI の JS 色演算は oklch の状態色トークンを扱えず、
// Alert・color="error" は本番テーマで描画時に例外になる。本番テーマで描画して検出する。
it("本番テーマで投入エラーと除外ダイアログを描画できる（状態色は oklch のまま）", async () => {
  mockIntake.mockRejectedValue(
    new ApiError(415, { code: "E_UNSUPPORTED_FORMAT" }),
  );
  render(
    <Providers>
      <IntakePage caseId={1} />
    </Providers>,
  );
  await userEvent.upload(
    screen.getByLabelText("ファイルを選択"),
    new File(["x"], "a.docx"),
  );
  const notice = (await screen.findByText(/未対応/)).closest('[role="alert"]');
  expect(notice).toHaveAttribute("data-tone", "danger");
  await userEvent.click(
    screen.getByRole("button", { name: "theme.txt を除外" }),
  );
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "除外する" })).toBeInTheDocument();
});
