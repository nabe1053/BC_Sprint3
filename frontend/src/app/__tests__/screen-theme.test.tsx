import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
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
  useIntakeDocument: () => ({}),
}));
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
