import Approval from "../(portal)/cases/[caseId]/versions/[versionId]/approval/page";
import InventoryReview from "../(portal)/cases/[caseId]/versions/[versionId]/inventory/page";
import Home from "../page";
import Cases from "../(portal)/cases/page";
import ItemReview from "../(portal)/cases/[caseId]/versions/[versionId]/page";
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
  CaseSelect: ({ caseId, target }: { caseId: number; target: string }) => (
    <div>
      select {caseId} {target}
    </div>
  ),
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

jest.mock("@/features/versions", () => ({
  ApprovalPage: ({
    caseId,
    versionId,
    caseSwitcher,
  }: {
    caseId: number;
    versionId: number;
    caseSwitcher?: React.ReactNode;
  }) => (
    <div>
      approval case {caseId} version {versionId}
      {caseSwitcher}
    </div>
  ),
  InventoryPage: ({
    caseId,
    versionId,
    caseSwitcher,
  }: {
    caseId: number;
    versionId: number;
    caseSwitcher?: React.ReactNode;
  }) => (
    <div>
      inventory case {caseId} version {versionId}
      {caseSwitcher}
    </div>
  ),
  ItemListPage: ({
    caseId,
    versionId,
    caseSwitcher,
  }: {
    caseId: number;
    versionId: number;
    caseSwitcher?: React.ReactNode;
  }) => (
    <div>
      case {caseId} version {versionId}
      {caseSwitcher}
    </div>
  ),
}));
it("版ルートは正整数の案件と版を公開featureへ渡す", async () => {
  renderWithProviders(
    await ItemReview({
      params: Promise.resolve({ caseId: "8", versionId: "9" }),
    }),
  );
  expect(screen.getByText("case 8 version 9")).toBeInTheDocument();
});
it.each(["0", "-1", "1.5", "abc", "9007199254740992"])(
  "版ルートは不正ID %s をどちらのパラメータでも拒否する",
  async (bad) => {
    await expect(
      ItemReview({ params: Promise.resolve({ caseId: bad, versionId: "9" }) }),
    ).rejects.toThrow("not found");
    await expect(
      ItemReview({ params: Promise.resolve({ caseId: "8", versionId: bad }) }),
    ).rejects.toThrow("not found");
  },
);

it("照合ルートは正整数の案件・版を公開featureへ渡す", async () => {
  renderWithProviders(
    await InventoryReview({
      params: Promise.resolve({ caseId: "8", versionId: "9" }),
    }),
  );
  expect(screen.getByText("inventory case 8 version 9")).toBeInTheDocument();
});
it.each(["0", "-1", "1.5", "abc", "9007199254740992"])(
  "照合ルートは不正ID %sを双方で拒否",
  async (bad) => {
    await expect(
      InventoryReview({
        params: Promise.resolve({ caseId: bad, versionId: "9" }),
      }),
    ).rejects.toThrow("not found");
    await expect(
      InventoryReview({
        params: Promise.resolve({ caseId: "8", versionId: bad }),
      }),
    ).rejects.toThrow("not found");
  },
);

it("承認ルートは正整数の案件と版を公開featureへ渡す", async () => {
  renderWithProviders(
    await Approval({
      params: Promise.resolve({ caseId: "8", versionId: "9" }),
    }),
  );
  expect(screen.getByText("approval case 8 version 9")).toBeInTheDocument();
});
it.each(["0", "-1", "1.5", "abc", "9007199254740992"])(
  "承認ルートは不正ID%sを双方で拒否",
  async (bad) => {
    await expect(
      Approval({ params: Promise.resolve({ caseId: bad, versionId: "9" }) }),
    ).rejects.toThrow("not found");
    await expect(
      Approval({ params: Promise.resolve({ caseId: "8", versionId: bad }) }),
    ).rejects.toThrow("not found");
  },
);

// F-14: SCR-03/05/06 に案件切替プルダウンを置く（memory AD-036 ③）。
it.each([
  [ItemReview, "items"],
  [InventoryReview, "inventory"],
  [Approval, "approval"],
] as const)(
  "版ルートは案件切替に同じ画面の行き先（%#）を渡す",
  async (Route, target) => {
    renderWithProviders(
      await Route({ params: Promise.resolve({ caseId: "8", versionId: "9" }) }),
    );
    expect(screen.getByText(`select 8 ${target}`)).toBeInTheDocument();
  },
);
