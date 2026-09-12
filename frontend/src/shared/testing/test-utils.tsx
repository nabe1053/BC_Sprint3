/**
 * テスト用の最小レンダリングヘルパー。
 *
 * T-103 の test-designer が用意（実装コードではなくテストインフラ）。
 * QueryClientProvider + i18next（実際の ja.json を使用）だけを提供する。
 * MUI テーマは本質的でないため意図的に含めない（必要になったら features 側の
 * テストが個別に Providers を使う）。トークン経由の見た目はこのヘルパーでは検証されない。
 * 複数フック間のinvalidateを観察するときは1回のrenderHookにまとめる。
 * 別Reactルートのresult.currentを使うと通知反映を安定して観察できない。
 */
import type { ReactElement, ReactNode } from "react";
import {
  render,
  renderHook,
  type RenderHookOptions,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import i18n from "@/shared/i18n";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function Wrapper({
  children,
  queryClient,
}: {
  children: ReactNode;
  queryClient: QueryClient;
}) {
  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </I18nextProvider>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  queryClient: QueryClient = createTestQueryClient(),
) {
  return {
    queryClient,
    ...render(ui, {
      wrapper: ({ children }) => (
        <Wrapper queryClient={queryClient}>{children}</Wrapper>
      ),
    }),
  };
}

export function renderHookWithProviders<TResult, TProps>(
  hook: (props: TProps) => TResult,
  queryClient: QueryClient = createTestQueryClient(),
  options?: Omit<RenderHookOptions<TProps>, "wrapper">,
) {
  return {
    queryClient,
    ...renderHook(hook, {
      ...options,
      wrapper: ({ children }) => (
        <Wrapper queryClient={queryClient}>{children}</Wrapper>
      ),
    }),
  };
}
