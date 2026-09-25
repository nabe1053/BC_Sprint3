import { fireEvent, screen, within, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { InventoryPage } from "../components/InventoryPage";
import * as hooks from "../hooks";
import { inventory, version } from "../testing/fixtures";
import { ApiError } from "@/shared/api/mutator";
import i18n from "@/shared/i18n";
jest.mock("../hooks");
const mock = jest.mocked(hooks),
  confirm = jest.fn(),
  undo = jest.fn(),
  refetch = jest.fn();
const query = (data: unknown) => ({
  data,
  isLoading: false,
  isError: false,
  error: null,
  refetch,
});
beforeEach(() => {
  jest.resetAllMocks();
  confirm.mockResolvedValue({});
  undo.mockResolvedValue({});
  mock.useVersion.mockReturnValue(query(version) as never);
  mock.useInventory.mockReturnValue(query(inventory) as never);
  mock.useCoverageMutations.mockReturnValue({
    confirm: { mutateAsync: confirm },
    undoConfirmation: { mutateAsync: undo },
  } as never);
});
const render = () =>
  renderWithProviders(<InventoryPage caseId={8} versionId={9} />);
const data = (changes: Partial<typeof inventory>) =>
  mock.useInventory.mockReturnValue(
    query({ ...inventory, ...changes }) as never,
  );
const name = () =>
  screen.getByRole("textbox", { name: "確認者名（取消時は取消者名）" });
it("見出し・9件数・前提注記・primary0・URL導線", () => {
  const { container } = render();
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "網羅性照合",
  );
  expect(container.querySelectorAll(".MuiButton-contained")).toHaveLength(0);
  expect(
    screen.getByText(
      "元資料 4 項目 → Item List 3 行（分割 1・除外 1・対応なし 1）",
    ),
  ).toBeInTheDocument();
  const dl = screen.getByRole("region", { name: "照合件数" });
  expect(dl.querySelectorAll("dt")).toHaveLength(9);
  expect(
    Array.from(dl.querySelectorAll("dd")).map((e) => e.textContent),
  ).toEqual(["5", "4", "3", "1", "1", "1", "1", "1", "2"]);
  expect(screen.queryByText("98765")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Item List へ" })).toHaveAttribute(
    "href",
    "/cases/8/versions/9",
  );
  expect(
    screen.getByText("対応なし 0 件は網羅性の保証ではありません"),
  ).toBeInTheDocument();
});
it("対応なし0でも前提の注記は表示", () => {
  data({ summary: { ...inventory.summary, unmappedEntryIds: [] } });
  render();
  expect(
    screen.getByText("対応なし 0 件は網羅性の保証ではありません"),
  ).toBeInTheDocument();
});
it("資料側の並びと2系統の状態を文字で識別し原文はリンク化しない", () => {
  render();
  const table = screen.getByRole("table", { name: "原明細一覧（資料側）" });
  const rows = within(table).getAllByRole("row").slice(1);
  expect(
    rows.map((row) => within(row).getAllByRole("cell")[0].textContent),
  ).toEqual(["p.5", "p.4", "p.1", "p.2", "p.3"]);
  expect(
    within(rows[0]).getByText(
      "不整合（記録された状態と対応関係が一致しません）",
    ),
  ).toBeInTheDocument();
  expect(within(rows[0]).getByText("記録: 対応済み")).toBeInTheDocument();
  expect(within(table).getByText("記録: 除外（脚注）")).toBeInTheDocument();
  expect(within(table).getByText("根拠: 共通条件を適用")).toBeInTheDocument();
  expect(
    within(table).getByText("<script>https://example.test</script>"),
  ).toBeInTheDocument();
  expect(table.querySelectorAll("a,script")).toHaveLength(0);
  expect(within(table).getByText("R1, R2")).toBeInTheDocument();
});
it("明細側の余分優先・候補区切り・多重対応・集計注記", () => {
  render();
  const table = screen.getByRole("table", {
    name: "Item List 対応表（明細側）",
  });
  const rows = within(table).getAllByRole("row").slice(1);
  expect(
    rows.map((row) => within(row).getByRole("rowheader").textContent),
  ).toEqual(["R3", "R1", "R2"]);
  expect(
    within(rows[0]).getByText("対応なし（余分の可能性）"),
  ).toBeInTheDocument();
  expect(within(table).getByText("G1 · A")).toBeInTheDocument();
  expect(within(table).getByText("多重対応（2 要素）")).toBeInTheDocument();
  expect(within(table).getByText("p.1（原項番 1）")).toBeInTheDocument();
  expect(
    screen.getByText(/元資料に対応元がない出力行 1 件/),
  ).toBeInTheDocument();
  expect(screen.getByText(/明細 4 件 → 出力 3 行/)).toBeInTheDocument();
});
it("資料名distinct・資料ごとの原本リンクにbaseURL/rel/別タブ", () => {
  render();
  const scope = screen.getByRole("region", { name: "照合する範囲" });
  expect(within(scope).getAllByText("明細.pdf")).toHaveLength(1);
  expect(within(scope).getByText("資料名を取得できません")).toBeInTheDocument();
  const links = within(scope).getAllByRole("link");
  expect(links).toHaveLength(2);
  expect(links.map((a) => a.getAttribute("href"))).toEqual([
    "http://localhost:8000/api/v1/ui/documents/1/file",
    "http://localhost:8000/api/v1/ui/documents/2/file",
  ]);
  for (const a of links) {
    expect(a).toHaveAttribute("target", "_blank");
    expect(a).toHaveAttribute("rel", "noopener noreferrer");
  }
  expect(
    within(scope).getByText(/この対応表に抽出漏れ検出機能はありません/),
  ).toBeInTheDocument();
});
it("空名でPOSTせず、trimした名前とkindだけを一度記録", async () => {
  render();
  expect(name()).toHaveValue("");
  expect(name()).toBeRequired();
  expect(screen.getByText("AI は補完しません")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "記録" }));
  expect(confirm).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toHaveTextContent(
    i18n.t("versions.inventory.recorderRequired"),
  );
  fireEvent.change(name(), { target: { value: "  確認者  " } });
  fireEvent.click(screen.getByRole("button", { name: "記録" }));
  await waitFor(() => expect(confirm).toHaveBeenCalledTimes(1));
  expect(confirm).toHaveBeenCalledWith({
    kind: "coverage",
    recordedBy: "確認者",
  });
});
it("送信中の二重操作をロックする", async () => {
  let finish: (value: unknown) => void = () => {};
  confirm.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  render();
  fireEvent.change(name(), { target: { value: "確認者" } });
  const button = screen.getByRole("button", { name: "記録" });
  fireEvent.click(button);
  fireEvent.click(button);
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(button).toBeDisabled();
  finish({});
  await waitFor(() => expect(button).not.toBeDisabled());
});
it("記録済みは応答名日時と取消のみ・取消者名必須でpath ID使用", async () => {
  data({
    summary: {
      ...inventory.summary,
      coverage: {
        confirmationId: 51,
        recordedBy: "応答者",
        recordedAt: "2026-09-13T01:23:45Z",
      },
    },
  });
  render();
  expect(
    screen.queryByRole("button", { name: "記録" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "更新" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByText("記録済み：応答者 / 2026-09-13T01:23:45Z"),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "取消" }));
  expect(undo).not.toHaveBeenCalled();
  fireEvent.change(name(), { target: { value: "  取消者 " } });
  fireEvent.click(screen.getByRole("button", { name: "取消" }));
  await waitFor(() =>
    expect(undo).toHaveBeenCalledWith({
      confirmationId: 51,
      recordedBy: "取消者",
    }),
  );
});
it.each([
  [409, "E_ALREADY_CONFIRMED"],
  [409, "E_ALREADY_UNDONE"],
  [404, "E_NOT_FOUND"],
  [400, "E_TARGET_INVALID"],
  [500, "E_UNKNOWN"],
] as const)("記録系%s/%sを固定文言にし生値を隠す", async (status, code) => {
  confirm.mockRejectedValue(
    new ApiError(status, {
      code,
      message: "private",
      details: { recordedBy: "secret" },
    }),
  );
  render();
  fireEvent.change(name(), { target: { value: "確認者" } });
  fireEvent.click(screen.getByRole("button", { name: "記録" }));
  const alert = await screen.findByRole("alert");
  const key =
    code === "E_ALREADY_CONFIRMED"
      ? "versions.inventory.errors.E_ALREADY_CONFIRMED"
      : code === "E_UNKNOWN"
        ? "versions.errors.unknown"
        : `versions.errors.${code}`;
  expect(alert).toHaveTextContent(i18n.t(key));
  expect(alert).not.toHaveTextContent("private");
  expect(alert).not.toHaveTextContent("secret");
  if (code === "E_ALREADY_CONFIRMED")
    expect(alert).not.toHaveTextContent(
      i18n.t("versions.errors.E_ALREADY_CONFIRMED"),
    );
  expect(confirm).toHaveBeenCalledTimes(1);
  fireEvent.click(within(alert).getByRole("button", { name: "再取得" }));
  expect(refetch).toHaveBeenCalledTimes(2);
});
it("読取中を明示する", () => {
  mock.useInventory.mockReturnValue({
    ...query(undefined),
    isLoading: true,
  } as never);
  render();
  expect(screen.getByRole("status")).toHaveTextContent(
    i18n.t("common.loading"),
  );
});
it.each(["version", "inventory"] as const)(
  "%sの404は版選び直しの導線",
  (resource) => {
    const target = resource === "version" ? mock.useVersion : mock.useInventory;
    target.mockReturnValue({
      ...query(undefined),
      isError: true,
      error: new ApiError(404, { code: "E_NOT_FOUND" }),
    } as never);
    render();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "版が見つかりません。案件一覧から版を選び直してください",
    );
    expect(screen.getByRole("link", { name: "案件一覧へ" })).toHaveAttribute(
      "href",
      "/cases",
    );
  },
);
it.each(["version", "inventory"] as const)(
  "%sの読取失敗は原因と再取得",
  (resource) => {
    const target = resource === "version" ? mock.useVersion : mock.useInventory;
    target.mockReturnValue({
      ...query(undefined),
      isError: true,
      error: new Error("private"),
    } as never);
    render();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "照合データを取得できませんでした。接続を確認して再取得してください",
    );
    fireEvent.click(screen.getByRole("button", { name: "再取得" }));
    expect(refetch).toHaveBeenCalledTimes(2);
  },
);
it("両側空なら案作成へ、片側空ならその表に該当なし", () => {
  data({ entries: [], items: [] });
  const view = render();
  expect(
    screen.getByText(
      "この版にはインベントリがありません。資料投入画面で案を作成してください",
    ),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "資料投入へ" })).toHaveAttribute(
    "href",
    "/cases/8/intake",
  );
  view.unmount();
  data({ entries: [] });
  render();
  expect(
    within(
      screen.getByRole("table", { name: "原明細一覧（資料側）" }),
    ).getByText("該当なし"),
  ).toBeInTheDocument();
});

test("notice explains extraction blind spots and uses polite record guidance", () => {
  const view = render();
  expect(
    screen.getByText(
      "この対応表は抽出できた範囲どうしの突合です。抽出処理が最初から読まなかったページ・別紙・後続メールは、元資料側にも出力側にも現れないため表では検出できません。全ページ・別紙・追加明細を元資料で確認してください。",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText("担当者確認済みにするには本記録が必要です"),
  ).toBeInTheDocument();
  view.unmount();
  data({
    summary: {
      ...inventory.summary,
      coverage: {
        confirmationId: 12,
        recordedBy: "確認者",
        recordedAt: "2026-09-13T00:00:00Z",
      },
    },
  });
  render();
  expect(
    screen.getByText("取り消すと前提は未達に戻ります"),
  ).toBeInTheDocument();
});
it("画面を戻って名前が空のまま取消すと、欄をエラーにして理由を示し再取得は出さない（TEST-11 #4）", async () => {
  data({
    summary: {
      ...inventory.summary,
      coverage: {
        confirmationId: 51,
        recordedBy: "応答者",
        recordedAt: "2026-09-13T01:23:45Z",
      },
    },
  });
  render();
  fireEvent.click(screen.getByRole("button", { name: "取消" }));
  expect(undo).not.toHaveBeenCalled();
  expect(name()).toHaveAttribute("aria-invalid", "true");
  expect(name()).toHaveAccessibleDescription(
    i18n.t("versions.inventory.recorderRequired"),
  );
  expect(
    screen.queryByRole("button", { name: "再取得" }),
  ).not.toBeInTheDocument();
  fireEvent.change(name(), { target: { value: "取消者" } });
  expect(name()).toHaveAttribute("aria-invalid", "false");
});
