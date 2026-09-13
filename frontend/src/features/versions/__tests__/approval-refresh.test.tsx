import { fireEvent, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { ItemListPage } from "../components/ItemListPage";
import { approvalData } from "../testing/fixtures";
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));
jest.mock("@/features/documents", () => ({
  useDocuments: () => ({ data: [], isLoading: false, isError: false }),
}));

it("評価確認済み版の訂正POST後、同一画面で版一覧を再取得して再確認バナーを出す", async () => {
  const original = global.fetch,
    data = approvalData();
  let saved = false;
  const request = jest.fn(
    async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = new URL(String(input)).pathname;
      let body: unknown,
        status = 200;
      if (
        path === "/api/v1/ui/versions/9/edits" &&
        options?.method === "POST"
      ) {
        saved = true;
        status = 201;
        body = { edits: data.records.edits };
      } else if (path === "/api/v1/ui/cases/8/versions") {
        body = {
          versions: [
            {
              ...data.listItem,
              currentState: saved ? "staff_checked" : "review_checked",
              needsRecheck: saved,
            },
          ],
        };
      } else if (path === "/api/v1/ui/versions/9") {
        body = {
          ...data.version,
          currentState: saved ? "staff_checked" : "review_checked",
        };
      } else if (path === "/api/v1/ui/versions/9/items") {
        body = { items: data.items };
      } else if (path === "/api/v1/ui/versions/9/questions") {
        body = { questions: data.questions };
      } else if (path === "/api/v1/ui/versions/9/items/4/evidence") {
        body = { evidences: [] };
      } else if (path === "/api/v1/ui/versions/9/exports") {
        // T-603: 版の履歴が出力履歴（#39）も読む。
        body = { exports: [] };
      } else throw new Error(`Unexpected request: ${path}`);
      return {
        ok: true,
        status,
        headers: new Headers({ "Content-Type": "application/json" }),
        json: async () => body,
      } as Response;
    },
  );
  global.fetch = request;
  try {
    renderWithProviders(<ItemListPage caseId={8} versionId={9} />);
    await screen.findByLabelText("担当者名（記録に共用）");
    expect(screen.queryByText(/再確認が必要/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("担当者名（記録に共用）"), {
      target: { value: "担当" },
    });
    await userEvent.click(
      screen.getAllByRole("button", { name: "詳細を見る" })[0],
    );
    const drawer = screen.getByRole("dialog");
    fireEvent.change(within(drawer).getByLabelText("対象項目"), {
      target: { value: "qty_value" },
    });
    fireEvent.change(within(drawer).getByLabelText("値の状態"), {
      target: { value: "tba" },
    });
    fireEvent.change(within(drawer).getByLabelText("修正理由（必須）"), {
      target: { value: "原資料を確認" },
    });
    const listCallsBeforeSave = request.mock.calls.filter(([url]) =>
      String(url).endsWith("/cases/8/versions"),
    ).length;
    await userEvent.click(
      within(drawer).getByRole("button", { name: "訂正を記録" }),
    );
    await waitFor(() => expect(screen.getByText(/再確認が必要/)).toBeVisible());
    const posts = request.mock.calls.filter(
      ([, options]) => options?.method === "POST",
    );
    expect(posts).toHaveLength(1);
    expect(JSON.parse(String(posts[0][1]?.body))).toEqual({
      itemId: 4,
      field: "qty_value",
      newState: "tba",
      reason: "原資料を確認",
      recordedBy: "担当",
    });
    expect(
      request.mock.calls.filter(([url]) =>
        String(url).endsWith("/cases/8/versions"),
      ),
    ).toHaveLength(listCallsBeforeSave + 1);
    expect(
      request.mock.calls.some(([url]) => String(url).endsWith("/records")),
    ).toBe(false);
  } finally {
    global.fetch = original;
  }
}, 30000);
