"use client";
import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AppShell } from "@/shared/ui";
import { useCases } from "../hooks";

/**
 * 左ナビに「案件の最新の確定版」を渡す（F-14・memory AD-036 ③）。
 * shared の AppShell は feature を知らないため、案件一覧の取得はここで行う。
 * layout に常駐して作り直されないため、画面を移るたびに取り直す（RV-057 P2）。
 * 案の作成完了は agent-runs が `CASES_QUERY_KEY` を無効化して知らせる。
 */
export function CaseShell({ children }: { children: ReactNode }) {
  const list = useCases();
  const pathname = usePathname();
  const { refetch } = list;
  const previous = useRef(pathname);
  useEffect(() => {
    if (previous.current === pathname) return;
    previous.current = pathname;
    void refetch();
  }, [pathname, refetch]);
  // 取得中・失敗は「不明」（undefined）、版の無い案件は null。
  const latestVersionOf = (caseId: number) =>
    list.data
      ? (list.data.find((item) => item.caseId === caseId)?.latestVersionId ??
        null)
      : undefined;
  return <AppShell latestVersionOf={latestVersionOf}>{children}</AppShell>;
}
