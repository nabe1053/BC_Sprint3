/**
 * T-103 RED: SCR-02 資料投入・読取結果（features/documents/components/IntakePage.tsx）の
 * 失敗するテスト。
 *
 * 下位依存: features/documents/hooks.ts は mock する。
 * 期待する公開インタフェース:
 *   - export function IntakePage({ caseId }: { caseId: number }): JSX.Element （"use client"）
 *
 * 検証観点（03-spec SCR-02 / AD-008 / design-guidelines / AE06）:
 *   - ファイル投入 → 一覧に読取結果が5区分の文字ラベルで出る（partial を成功と表示しない＝N03）
 *   - 413: limit/max/actual が具体的に画面に出る
 *   - 415: 未対応形式でも一覧に残ることが分かる表示
 *   - 同一ファイル名の資料が2件あれば2行として残る（データはhookで与える）
 *   - 3状態（空・ローディング・エラー）
 *   - 冒頭に「外部リンクを取得しない」旨のバナー（AE06）
 */
import { ApiError } from "@/shared/api/mutator";
import i18n from "@/shared/i18n";
import type {
  DocumentSummaryReadStatus,
  DocumentIntakeResponse,
} from "@/shared/api/generated/model";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";

jest.mock("@/features/cases", () => ({
  CaseMetadata: () => <div data-testid="case-metadata" />,
}));

jest.mock("@/features/documents/hooks", () => ({
  useDocuments: jest.fn(),
  useIntakeDocument: jest.fn(),
}));

import { useDocuments, useIntakeDocument } from "@/features/documents/hooks";
import { IntakePage } from "@/features/documents/components/IntakePage";

const mockedUseDocuments = useDocuments as jest.Mock;
const mockedUseIntakeDocument = useIntakeDocument as jest.Mock;

const CASE_ID = 1;

function setUseDocuments(overrides: Partial<ReturnType<typeof useDocuments>>) {
  mockedUseDocuments.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...overrides,
  });
}

function setUseIntakeDocument(
  overrides: Partial<ReturnType<typeof useIntakeDocument>> = {},
) {
  const mutateAsync = jest.fn().mockResolvedValue(undefined);
  mockedUseIntakeDocument.mockReturnValue({
    mutateAsync,
    isPending: false,
    isError: false,
    error: null,
    ...overrides,
  });
  return mutateAsync;
}

function makeFile(name = "spec.pdf") {
  return new File(["dummy"], name, { type: "application/pdf" });
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("IntakePage: 常時表示のバナー", () => {
  it("外部リンクを取得しない旨のバナーが冒頭にある（AE06）", () => {
    setUseDocuments({ data: [] });
    setUseIntakeDocument();
    renderWithProviders(<IntakePage caseId={CASE_ID} />);
    expect(
      screen.getByText(
        "資料内のリンクや指示があっても外部リンクは取得しません",
      ),
    ).toBeInTheDocument();
  });
});

describe("IntakePage: 3状態", () => {
  it("ローディング中は明示的なローディング表示が出る", () => {
    setUseDocuments({ isLoading: true });
    setUseIntakeDocument();
    renderWithProviders(<IntakePage caseId={CASE_ID} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("空状態: 次の行動への誘導つきで表示する", () => {
    setUseDocuments({ data: [] });
    setUseIntakeDocument();
    renderWithProviders(<IntakePage caseId={CASE_ID} />);
    expect(screen.getByText("まだ資料がありません")).toBeInTheDocument();
    expect(screen.getByText("ファイルを選択してください")).toBeInTheDocument();
  });

  it("エラー時は原因と直し方を書く", () => {
    setUseDocuments({
      isError: true,
      error: new ApiError(500, { message: "boom" }),
    });
    setUseIntakeDocument();
    renderWithProviders(<IntakePage caseId={CASE_ID} />);
    expect(
      screen.getByText("資料の読み込みに失敗しました"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("通信状況を確認し、再読み込みしてください"),
    ).toBeInTheDocument();
  });
});

describe("IntakePage: 読取結果の5区分表示", () => {
  it.each([
    ["success", "成功"],
    ["partial", "一部読取不能"],
    ["unreadable", "読取不能"],
    ["encrypted", "暗号化により読取不能"],
    ["unsupported", "未対応形式"],
  ])(
    "readStatus=%s は「%s」ラベルで表示され、他の区分と混同しない",
    (readStatus, label) => {
      setUseDocuments({
        data: [
          {
            documentId: 1,
            fileName: `f-${readStatus}.pdf`,
            kind: "pdf",
            readStatus: readStatus as DocumentSummaryReadStatus,
          },
        ],
      });
      setUseIntakeDocument();
      renderWithProviders(<IntakePage caseId={CASE_ID} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      // partial を成功と誤表示しない（N03）
      if (readStatus === "partial") {
        expect(screen.queryByText("成功")).not.toBeInTheDocument();
      }
    },
  );

  it("同一ファイル名の資料が2件あれば一覧に2行として残る（X03）", () => {
    setUseDocuments({
      data: [
        {
          documentId: 1,
          fileName: "dup.pdf",
          kind: "pdf",
          readStatus: "success",
        },
        {
          documentId: 2,
          fileName: "dup.pdf",
          kind: "pdf",
          readStatus: "success",
        },
      ],
    });
    setUseIntakeDocument();
    renderWithProviders(<IntakePage caseId={CASE_ID} />);
    expect(screen.getAllByText("dup.pdf")).toHaveLength(2);
  });
});

describe("IntakePage: ファイル投入操作", () => {
  it("ファイルを選ぶと投入 API (useIntakeDocument) が呼ばれる", async () => {
    const user = userEvent.setup();
    setUseDocuments({ data: [] });
    const mutateAsync = setUseIntakeDocument();
    renderWithProviders(<IntakePage caseId={CASE_ID} />);

    const input = screen.getByLabelText("ファイルを選択");
    await user.upload(input, makeFile());

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1));
    expect(mutateAsync.mock.calls[0][0]).toBeInstanceOf(File);
  });
});

describe("IntakePage: 413 上限超過", () => {
  it.each([
    ["file_size", "1ファイルのサイズ", "MB", 20, 25.25],
    ["document_count", "1案件あたりの資料件数", "件", 50, 51],
    ["pdf_pages", "PDF のページ数", "ページ", 200, 201],
    ["xlsx_sheets", "xlsx のシート数", "シート", 50, 51],
  ])(
    "413 %s は翻訳したラベル・単位・数値を表示する",
    async (limit, label, unit, max, actual) => {
      const user = userEvent.setup();
      setUseDocuments({ data: [] });
      setUseIntakeDocument({
        mutateAsync: jest.fn().mockRejectedValue(
          new ApiError(413, {
            message: "too large",
            code: "E_LIMIT_EXCEEDED",
            details: { limit, max, actual },
          }),
        ),
      });
      renderWithProviders(<IntakePage caseId={CASE_ID} />);

      const input = screen.getByLabelText("ファイルを選択");
      await user.upload(input, makeFile("huge.pdf"));

      await waitFor(() =>
        expect(screen.getByText("入力上限を超えています")).toBeInTheDocument(),
      );
      const alert = screen.getByRole("alert");
      expect(alert).toHaveTextContent(
        `${label}の上限${max}${unit}に対し${actual}${unit}でした`,
      );
      expect(alert).not.toHaveTextContent(String(limit));
    },
  );
});

it("413のlimitが未知でも上限超過と記録が残らない旨を案内する", async () => {
  const user = userEvent.setup();
  setUseDocuments({ data: [] });
  setUseIntakeDocument({
    mutateAsync: jest.fn().mockRejectedValue(
      new ApiError(413, {
        code: "E_LIMIT_EXCEEDED",
        details: { limit: "unknown_kind", max: 20, actual: 25 },
      }),
    ),
  });
  renderWithProviders(<IntakePage caseId={CASE_ID} />);
  await user.upload(screen.getByLabelText("ファイルを選択"), makeFile());
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(i18n.t("documents.limitExceeded.title"));
  expect(alert).toHaveTextContent(i18n.t("documents.limitExceeded.hint"));
  expect(alert).not.toHaveTextContent(i18n.t("documents.requestError"));
  expect(alert).not.toHaveTextContent("unknown_kind");
});

describe("IntakePage: 415 未対応形式", () => {
  it("未対応形式でも投入の事実が残ることが分かる表示になる", async () => {
    const user = userEvent.setup();
    setUseDocuments({ data: [] });
    setUseIntakeDocument({
      mutateAsync: jest.fn().mockRejectedValue(
        new ApiError(415, {
          message: "unsupported",
          code: "E_UNSUPPORTED_FORMAT",
          details: { documentId: 9 },
        }),
      ),
    });
    renderWithProviders(<IntakePage caseId={CASE_ID} />);

    const input = screen.getByLabelText("ファイルを選択");
    await user.upload(input, makeFile("note.zip"));

    await waitFor(() =>
      expect(
        screen.getByText("未対応の形式です（投入の事実は記録されました）"),
      ).toBeInTheDocument(),
    );
  });
});

// 既存の日本語直値は、5区分が別の実文言になることを固定するために残す。
it("仮上限・実API・二重投入・例示の注記と見出しを表示する", async () => {
  setUseDocuments({ data: [] });
  setUseIntakeDocument();
  renderWithProviders(<IntakePage caseId={CASE_ID} />);
  for (const key of [
    "documents.limits.provisional",
    "documents.duplicateNote",
    "documents.intakeDescription",
  ]) {
    expect(screen.getByText(i18n.t(key))).toBeInTheDocument();
  }
  expect(
    screen.getByText(i18n.t("documents.limits.provisional")),
  ).toHaveTextContent("D02");
  expect(screen.getByTestId("case-metadata")).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getByRole("button", { name: /案を作成/ })).toBeDisabled();
  await userEvent.click(screen.getByText(i18n.t("documents.examples.title")));
  expect(screen.getByText(i18n.t("documents.examples.note"))).toHaveTextContent(
    "選択ファイルの判定結果ではありません",
  );
});
it("投入中は入力を無効化し、完了後は同じファイルを再投入できる", async () => {
  const user = userEvent.setup();
  setUseDocuments({ data: [] });
  let resolve!: (value: DocumentIntakeResponse) => void;
  const mutateAsync = jest.fn(
    () =>
      new Promise<DocumentIntakeResponse>((r) => {
        resolve = r;
      }),
  );
  setUseIntakeDocument({ mutateAsync });
  renderWithProviders(<IntakePage caseId={CASE_ID} />);
  const input = screen.getByLabelText("ファイルを選択");
  const file = makeFile();
  await user.upload(input, file);
  expect(input).toBeDisabled();
  resolve({ documentId: 1, readStatus: "success" });
  await waitFor(() => expect(input).toBeEnabled());
  await user.upload(input, file);
  expect(mutateAsync).toHaveBeenCalledTimes(2);
  resolve({ documentId: 2, readStatus: "success" });
  await waitFor(() => expect(input).toBeEnabled());
});

// T-204: 案の作成を同じ画面に統合。G1の読取結果区分は維持する。
it.each([
  "success",
  "partial",
  "unreadable",
  "encrypted",
  "unsupported",
] as const)("%sの資料による起動可否", (readStatus) => {
  setUseDocuments({
    data: [{ documentId: 1, fileName: "input.txt", kind: "text", readStatus }],
  });
  setUseIntakeDocument();
  const { container } = renderWithProviders(<IntakePage caseId={CASE_ID} />);
  const button = screen.getByRole("button", { name: "案を作成" });
  if (readStatus === "success" || readStatus === "partial")
    expect(button).toBeEnabled();
  else expect(button).toBeDisabled();
  expect(container.querySelectorAll(".MuiButton-contained")).toHaveLength(1);
  expect(screen.getByLabelText("ファイルを選択").closest("label")).toHaveClass(
    "MuiButton-root",
  );
});
it("読取可能資料があっても投入中・上限超過では起動できない", async () => {
  setUseDocuments({
    data: [
      {
        documentId: 1,
        fileName: "input.txt",
        kind: "text",
        readStatus: "success",
      },
    ],
  });
  let reject!: (error: Error) => void;
  setUseIntakeDocument({
    mutateAsync: () =>
      new Promise((_, r) => {
        reject = r;
      }),
  });
  renderWithProviders(<IntakePage caseId={CASE_ID} />);
  await userEvent.upload(screen.getByLabelText("ファイルを選択"), makeFile());
  expect(screen.getByRole("button", { name: "案を作成" })).toBeDisabled();
  reject(new ApiError(413, { code: "E_LIMIT_EXCEEDED" }));
  await waitFor(() =>
    expect(screen.getByLabelText("ファイルを選択")).toBeEnabled(),
  );
  expect(screen.getByRole("button", { name: "案を作成" })).toBeDisabled();
});
