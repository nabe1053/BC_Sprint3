import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { ExportButton } from "../components/ExportButton";
import * as api from "../api";
// hooks は mock しない。mutationKey / useIsMutating / lock の実配線を検査する。
jest.mock("../api");
const mock = jest.mocked(api);

beforeEach(() => {
  jest.resetAllMocks();
  global.URL.createObjectURL = jest.fn(() => "blob:x");
  global.URL.revokeObjectURL = jest.fn();
});

it("同じ版の出力ボタンが2つあっても、同時にPOSTされない（版単位の共有ロック）", async () => {
  let release: (value: unknown) => void = () => {};
  mock.createExport.mockImplementation(
    () =>
      new Promise((resolve) => {
        release = resolve;
      }) as never,
  );
  renderWithProviders(
    <>
      <ExportButton versionId={9} label="現在の記録を出力" />
      <ExportButton versionId={9} label="版 1 を出力" />
    </>,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "現在の記録を出力" }),
  );
  // 片方を押すと同じ版のボタンはすべて「出力中…」になる。
  await waitFor(() =>
    expect(screen.getAllByRole("button", { name: "出力中…" })).toHaveLength(2),
  );
  expect(
    screen
      .getAllByRole("button", { name: "出力中…" })
      .every((b) => b.hasAttribute("disabled")),
  ).toBe(true);
  release({
    blob: new Blob(["x"]),
    fileName: "S-01__v2_draft.xlsx",
    namedByServer: true,
  });
  await waitFor(() => expect(mock.createExport).toHaveBeenCalledTimes(1));
  expect(mock.createExport).toHaveBeenCalledWith(9);
});

it("別の版のボタンは巻き込まれない", async () => {
  mock.createExport.mockImplementation(() => new Promise(() => {}) as never);
  renderWithProviders(
    <>
      <ExportButton versionId={9} label="版 1 を出力" />
      <ExportButton versionId={10} label="版 2 を出力" />
    </>,
  );
  await userEvent.click(screen.getByRole("button", { name: "版 1 を出力" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "出力中…" })).toBeDisabled(),
  );
  expect(screen.getByRole("button", { name: "版 2 を出力" })).toBeEnabled();
});
