/**
 * T-103 RED: features/documents/hooks.ts の失敗するテスト。
 *
 * 責務: 資料一覧の取得（3状態）・資料投入（成功 / 413 E_LIMIT_EXCEEDED / 415
 * E_UNSUPPORTED_FORMAT）。AD-005: 415 は「投入の事実を記録した上でのエラー」
 * なので一覧を再取得する。413 は記録を残さないので一覧を再取得しない。
 *
 * 下位依存: features/documents/api.ts は mock する。
 * 期待する公開インタフェース:
 *   - useDocuments(caseId: number): { data, isLoading, isError, error }
 *   - useIntakeDocument(caseId: number): UseMutationResult<DocumentIntakeResponse, ApiError, File>
 */
import { act, waitFor } from "@testing-library/react";
import { ApiError } from "@/shared/api/mutator";
import {
  renderHookWithProviders,
  createTestQueryClient,
} from "@/shared/testing/test-utils";

jest.mock("@/features/documents/api", () => ({
  listDocuments: jest.fn(),
  intakeDocument: jest.fn(),
}));

import { listDocuments, intakeDocument } from "@/features/documents/api";
import { useDocuments, useIntakeDocument } from "@/features/documents/hooks";

const mockedListDocuments = listDocuments as jest.MockedFunction<
  typeof listDocuments
>;
const mockedIntakeDocument = intakeDocument as jest.MockedFunction<
  typeof intakeDocument
>;

const CASE_ID = 1;

function makeFile(name = "spec.pdf") {
  return new File(["dummy"], name, { type: "application/pdf" });
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useDocuments", () => {
  it("ローディング中は isLoading が true になる", () => {
    mockedListDocuments.mockReturnValue(new Promise(() => {}));
    const { result } = renderHookWithProviders(() => useDocuments(CASE_ID));
    expect(result.current.isLoading).toBe(true);
  });

  it("成功すると資料一覧を返す", async () => {
    mockedListDocuments.mockResolvedValue([
      {
        documentId: 1,
        fileName: "a.pdf",
        kind: "pdf",
        readStatus: "success",
        pageCount: 1,
        unreadableLocators: [],
      },
    ]);
    const { result } = renderHookWithProviders(() => useDocuments(CASE_ID));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.isError).toBe(false);
  });

  it("失敗すると isError=true になる", async () => {
    mockedListDocuments.mockRejectedValue(
      new ApiError(500, { code: "E_UNKNOWN" }),
    );
    const { result } = renderHookWithProviders(() => useDocuments(CASE_ID));
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useIntakeDocument", () => {
  it("投入成功後に資料一覧(useDocuments)が再取得される", async () => {
    mockedListDocuments.mockResolvedValueOnce([]).mockResolvedValueOnce([
      {
        documentId: 1,
        fileName: "a.pdf",
        kind: "pdf",
        readStatus: "success",
        pageCount: 1,
        unreadableLocators: [],
      },
    ]);
    mockedIntakeDocument.mockResolvedValue({
      documentId: 1,
      readStatus: "success",
    });

    const queryClient = createTestQueryClient();
    const { result } = renderHookWithProviders(
      () => ({
        list: useDocuments(CASE_ID),
        intake: useIntakeDocument(CASE_ID),
      }),
      queryClient,
    );
    await waitFor(() => expect(result.current.list.isLoading).toBe(false));

    await act(async () => {
      await result.current.intake.mutateAsync(makeFile());
    });

    await waitFor(() => expect(mockedListDocuments).toHaveBeenCalledTimes(2));
  });

  it.each(["file_size", "document_count", "pdf_pages", "xlsx_sheets"])(
    "413 %s E_LIMIT_EXCEEDED は limit/max/actual を details として持ち、一覧は再取得されない（記録が残らないため）",
    async (limit) => {
      mockedListDocuments.mockResolvedValue([]);
      mockedIntakeDocument.mockRejectedValue(
        new ApiError(413, {
          code: "E_LIMIT_EXCEEDED",
          message: "too large",
          details: { limit, max: 20, actual: 25 },
        }),
      );

      const queryClient = createTestQueryClient();
      const { result } = renderHookWithProviders(
        () => ({
          list: useDocuments(CASE_ID),
          intake: useIntakeDocument(CASE_ID),
        }),
        queryClient,
      );
      await waitFor(() => expect(result.current.list.isLoading).toBe(false));
      expect(mockedListDocuments).toHaveBeenCalledTimes(1);

      await act(async () => {
        await expect(
          result.current.intake.mutateAsync(makeFile()),
        ).rejects.toBeInstanceOf(ApiError);
      });

      await waitFor(() => expect(result.current.intake.isError).toBe(true));
      const error = result.current.intake.error as ApiError;
      expect(error.code).toBe("E_LIMIT_EXCEEDED");
      expect(error.details).toEqual({ limit, max: 20, actual: 25 });
      // 記録が残らない失敗なので一覧の再取得は起きない。
      expect(mockedListDocuments).toHaveBeenCalledTimes(1);
    },
  );

  it("415 E_UNSUPPORTED_FORMAT は details.documentId を持ち、投入の事実が記録されるため一覧が再取得される", async () => {
    mockedListDocuments.mockResolvedValueOnce([]).mockResolvedValueOnce([
      {
        documentId: 9,
        fileName: "note.zip",
        kind: "unsupported",
        readStatus: "unsupported",
        pageCount: 1,
        unreadableLocators: [],
      },
    ]);
    mockedIntakeDocument.mockRejectedValue(
      new ApiError(415, {
        code: "E_UNSUPPORTED_FORMAT",
        message: "unsupported",
        details: { documentId: 9 },
      }),
    );

    const queryClient = createTestQueryClient();
    const { result } = renderHookWithProviders(
      () => ({
        list: useDocuments(CASE_ID),
        intake: useIntakeDocument(CASE_ID),
      }),
      queryClient,
    );
    await waitFor(() => expect(result.current.list.isLoading).toBe(false));

    await act(async () => {
      await expect(
        result.current.intake.mutateAsync(makeFile("note.zip")),
      ).rejects.toBeInstanceOf(ApiError);
    });

    await waitFor(() => expect(result.current.intake.isError).toBe(true));
    const error = result.current.intake.error as ApiError;
    expect(error.code).toBe("E_UNSUPPORTED_FORMAT");
    expect((error.details as { documentId: number }).documentId).toBe(9);

    await waitFor(() => expect(mockedListDocuments).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(result.current.list.data).toEqual([
        {
          documentId: 9,
          fileName: "note.zip",
          kind: "unsupported",
          readStatus: "unsupported",
          pageCount: 1,
          unreadableLocators: [],
        },
      ]),
    );
  });

  it("同一ファイルを2回投入すると api.intakeDocument が2回呼ばれ、一覧が2回再取得される（X03: 二重投入は両方残す）", async () => {
    mockedListDocuments.mockResolvedValue([]);
    mockedIntakeDocument
      .mockResolvedValueOnce({ documentId: 1, readStatus: "success" })
      .mockResolvedValueOnce({ documentId: 2, readStatus: "success" });

    const queryClient = createTestQueryClient();
    const { result } = renderHookWithProviders(
      () => ({
        list: useDocuments(CASE_ID),
        intake: useIntakeDocument(CASE_ID),
      }),
      queryClient,
    );
    await waitFor(() => expect(mockedListDocuments).toHaveBeenCalledTimes(1));

    const file = makeFile("dup.pdf");

    await act(async () => {
      await result.current.intake.mutateAsync(file);
    });
    await act(async () => {
      await result.current.intake.mutateAsync(file);
    });

    expect(mockedIntakeDocument).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(mockedListDocuments).toHaveBeenCalledTimes(3));
  });
});
