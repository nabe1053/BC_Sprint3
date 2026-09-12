import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { Providers } from "../providers";
import { ApiError } from "@/shared/api/mutator";

jest.mock("@mui/material-nextjs/v15-appRouter", () => ({
  AppRouterCacheProvider: ({ children }: { children: ReactNode }) => children,
}));

it("本番Providersの記録系POSTは自動再送しない（415でも1回）", async () => {
  let client!: QueryClient;
  function Probe() {
    client = useQueryClient();
    return <span>ready</span>;
  }
  render(
    <Providers>
      <Probe />
    </Providers>,
  );
  expect(screen.getByText("ready")).toBeInTheDocument();
  expect(client.getDefaultOptions().mutations?.retry).toBe(false);
  const post = jest
    .fn()
    .mockRejectedValue(new ApiError(415, { code: "E_UNSUPPORTED_FORMAT" }));
  const mutation = client
    .getMutationCache()
    .build(client, { mutationFn: post });
  await expect(mutation.execute(undefined)).rejects.toBeInstanceOf(ApiError);
  expect(post).toHaveBeenCalledTimes(1);
  client.clear();
});
