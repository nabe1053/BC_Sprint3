/**
 * T-103 RED: features/cases/hooks.ts の失敗するテスト。
 *
 * 責務: 案件一覧の取得（3状態）・案件作成（成功で一覧再取得 / 409・422 を
 * ApiError.code で区別できること）。
 *
 * 下位依存: features/cases/api.ts は mock する（実装しない。実装は implementer）。
 * 期待する公開インタフェース:
 *   - useCases(): { data: CaseListItem[] | undefined; isLoading: boolean; isError: boolean; error: unknown }
 *   - useCreateCase(): UseMutationResult<CaseResponse, ApiError, CreateCaseInput>
 *     成功時に useCases のキャッシュを無効化し再取得させる。
 */
import { act, waitFor } from "@testing-library/react";
import { ApiError } from "@/shared/api/mutator";
import {
  renderHookWithProviders,
  createTestQueryClient,
} from "@/shared/testing/test-utils";

// features/cases/api.ts は未実装（このテストが RED の起点）。
jest.mock("@/features/cases/api", () => ({
  listCases: jest.fn(),
  createCase: jest.fn(),
}));

import { listCases, createCase } from "@/features/cases/api";
import { useCases, useCreateCase } from "@/features/cases/hooks";

const mockedListCases = listCases as jest.MockedFunction<typeof listCases>;
const mockedCreateCase = createCase as jest.MockedFunction<typeof createCase>;

const sampleCase = {
  caseId: 1,
  caseCode: "S04",
  customerName: "顧客A",
  title: "OCTG 引合",
  createdAt: "2026-09-01T00:00:00+09:00",
  progressStatus: "intake" as const,
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useCases", () => {
  it("ローディング中は isLoading が true になる", async () => {
    mockedListCases.mockReturnValue(new Promise(() => {}));

    const { result } = renderHookWithProviders(() => useCases());

    expect(result.current.isLoading).toBe(true);
  });

  it("成功すると一覧データを isLoading=false で返す", async () => {
    mockedListCases.mockResolvedValue([sampleCase]);

    const { result } = renderHookWithProviders(() => useCases());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(false);
    expect(result.current.data).toEqual([sampleCase]);
  });

  it("失敗すると isError=true になり呼び出し側がエラーを判別できる", async () => {
    mockedListCases.mockRejectedValue(
      new ApiError(500, { code: "E_UNKNOWN", message: "boom" }),
    );

    const { result } = renderHookWithProviders(() => useCases());

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useCreateCase", () => {
  it("作成成功後に一覧(useCases)が再取得される（キャッシュ無効化）", async () => {
    mockedListCases
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([sampleCase]);
    mockedCreateCase.mockResolvedValue({
      caseId: 1,
      caseCode: "S04",
      customerName: null,
      title: null,
      createdAt: "2026-09-01T00:00:00+09:00",
    });

    const queryClient = createTestQueryClient();
    const { result } = renderHookWithProviders(
      () => ({ list: useCases(), create: useCreateCase() }),
      queryClient,
    );
    await waitFor(() => expect(result.current.list.isLoading).toBe(false));
    expect(mockedListCases).toHaveBeenCalledTimes(1);

    await act(async () => {
      await result.current.create.mutateAsync({ caseCode: "S04" });
    });

    await waitFor(() => expect(mockedListCases).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.list.data).toEqual([sampleCase]));
  });

  it("重複した照会番号(409 E_DUPLICATE_CASE_CODE)を呼び出し側が判別できる", async () => {
    mockedCreateCase.mockRejectedValue(
      new ApiError(409, {
        code: "E_DUPLICATE_CASE_CODE",
        message: "duplicate",
      }),
    );

    const { result } = renderHookWithProviders(() => useCreateCase());

    await act(async () => {
      await expect(
        result.current.mutateAsync({ caseCode: "DUP" }),
      ).rejects.toBeInstanceOf(ApiError);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as ApiError).code).toBe(
      "E_DUPLICATE_CASE_CODE",
    );
  });

  it("入力検証エラー(422)を呼び出し側が判別できる", async () => {
    mockedCreateCase.mockRejectedValue(
      new ApiError(422, { code: "E_VALIDATION", message: "invalid" }),
    );

    const { result } = renderHookWithProviders(() => useCreateCase());

    await act(async () => {
      await expect(
        result.current.mutateAsync({ caseCode: "" }),
      ).rejects.toBeInstanceOf(ApiError);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as ApiError).status).toBe(422);
  });
});
