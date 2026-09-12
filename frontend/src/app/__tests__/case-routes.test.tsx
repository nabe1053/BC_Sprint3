import Home from "../page";
import Cases from "../(portal)/cases/page";
import Intake from "../(portal)/cases/[caseId]/intake/page";
import { redirect, notFound } from "next/navigation";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { screen } from "@testing-library/react";
jest.mock("next/navigation", () => ({
  redirect: jest.fn(),
  notFound: jest.fn(() => {
    throw new Error("not found");
  }),
}));
jest.mock("@/features/cases", () => ({
  CaseListPage: () => <div>cases view</div>,
}));
jest.mock("@/features/documents", () => ({
  IntakePage: ({ caseId }: { caseId: number }) => <div>case {caseId}</div>,
}));
it("トップはcasesへリダイレクトする", () => {
  Home();
  expect(redirect).toHaveBeenCalledWith("/cases");
});
it("案件一覧は公開featureを表示する", () => {
  renderWithProviders(<Cases />);
  expect(screen.getByText("cases view")).toBeInTheDocument();
});
it("投入ルートは正整数caseIdを画面へ渡す", async () => {
  renderWithProviders(
    await Intake({ params: Promise.resolve({ caseId: "8" }) }),
  );
  expect(screen.getByText("case 8")).toBeInTheDocument();
});
it.each(["0", "-1", "1.5", "abc", "9007199254740992"])(
  "不正caseId %s はnotFound",
  async (caseId) => {
    await expect(
      Intake({ params: Promise.resolve({ caseId }) }),
    ).rejects.toThrow("not found");
    expect(notFound).toHaveBeenCalled();
  },
);
