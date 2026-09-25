"use client";
import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";

const { colors, spacing, radius, shadow, border, typography, layout, z } =
  tokens;

/** 左ナビの並び。SCR-04 根拠詳細はドロワーのため項目を持たない（モックと同じ）。 */
const NAV = [
  { key: "cases", href: () => "/cases" },
  {
    key: "intake",
    href: (c: string | null) => (c ? `/cases/${c}/intake` : null),
  },
  {
    key: "items",
    href: (c: string | null, v: string | null) =>
      c && v ? `/cases/${c}/versions/${v}` : null,
  },
  {
    key: "inventory",
    href: (c: string | null, v: string | null) =>
      c && v ? `/cases/${c}/versions/${v}/inventory` : null,
  },
  {
    key: "approval",
    href: (c: string | null, v: string | null) =>
      c && v ? `/cases/${c}/versions/${v}/approval` : null,
  },
] as const;

/** URL から案件・版を取り出す（画面間の移動に必要な文脈はルートが持つ。AD-024 ①）。 */
export function routeContext(pathname: string) {
  const caseId = /^\/cases\/(\d+)(\/|$)/.exec(pathname)?.[1] ?? null;
  const versionId =
    /^\/cases\/\d+\/versions\/(\d+)(\/|$)/.exec(pathname)?.[1] ?? null;
  return { caseId, versionId };
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const pathname = usePathname() ?? "";
  const { caseId, versionId } = routeContext(pathname);
  const [collapsed, setCollapsed] = useState(false);
  const navWidth = collapsed ? layout.navWidthCollapsed : layout.navWidth;
  return (
    <>
      <Box
        component="header"
        sx={{
          position: "fixed",
          top: 0,
          left: 0,
          width: `${navWidth}px`,
          height: `${layout.shellHeight}px`,
          zIndex: z.header,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: collapsed ? "center" : "stretch",
          gap: "2px",
          padding: collapsed ? 0 : `0 ${spacing.s8}px 0 ${spacing.s4}px`,
          background: colors.a[100],
          borderRight: `${border.width}px solid ${colors.a[200]}`,
          borderBottom: `${border.width}px solid ${colors.a[200]}`,
        }}
      >
        <Box
          component="button"
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
          aria-controls="app-nav"
          aria-label={t(collapsed ? "shell.navOpen" : "shell.navClose")}
          sx={{
            position: collapsed ? "static" : "absolute",
            right: `${spacing.s2}px`,
            top: collapsed ? "auto" : "50%",
            transform: collapsed ? "none" : "translateY(-50%)",
            width: "26px",
            height: "26px",
            padding: 0,
            border: `${border.width}px solid ${colors.divider}`,
            borderRadius: `${radius.sm}px`,
            background: "transparent",
            color: colors.n[700],
            fontSize: `${typography.size.fs4}px`,
            lineHeight: 1,
            cursor: "pointer",
            "&:hover": { background: colors.surface },
          }}
        >
          {collapsed ? "›" : "‹"}
        </Box>
        {!collapsed && (
          <Typography
            component="b"
            sx={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              // 232px の左ナビ幅で 1 行に収める（fs4 では最後の 1 字が折り返す）。
              fontSize: `${typography.size.fs3}px`,
              fontWeight: typography.weight.bold,
              lineHeight: 1.1,
              whiteSpace: "nowrap",
            }}
          >
            <Box
              aria-hidden="true"
              sx={{
                display: "grid",
                placeItems: "center",
                width: "26px",
                height: "26px",
                borderRadius: `${radius.sm}px`,
                boxShadow: shadow.sm,
                background: colors.accent,
                color: colors.onDark,
                fontWeight: typography.weight.bold,
                fontSize: `${typography.size.fs3}px`,
                flex: "none",
              }}
            >
              {t("shell.brandMark")}
            </Box>
            <span>{t("shell.brand")}</span>
          </Typography>
        )}
      </Box>
      <Box
        component="nav"
        id="app-nav"
        aria-label={t("shell.navLabel")}
        sx={{
          position: "fixed",
          top: `${layout.shellHeight}px`,
          bottom: 0,
          left: 0,
          width: `${navWidth}px`,
          zIndex: z.nav,
          display: "flex",
          flexDirection: "column",
          gap: "2px",
          padding: collapsed
            ? `${spacing.s4}px ${spacing.s1}px`
            : `${spacing.s4}px ${spacing.s2}px`,
          overflowY: "auto",
          background: colors.a[100],
          borderRight: `${border.width}px solid ${colors.a[200]}`,
          boxShadow: shadow.sm,
        }}
      >
        {NAV.map((item, index) => {
          const num = String(index + 1).padStart(2, "0");
          const href = item.href(caseId, versionId);
          const name = t(`shell.nav.${item.key}`);
          const active = href !== null && pathname === href;
          const shared = {
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "flex-start",
            gap: "10px",
            padding: collapsed ? "12px 0" : "10px 10px 10px 12px",
            borderRadius: `${radius.md}px`,
            fontSize: `${typography.size.fs4}px`,
            lineHeight: 1.35,
            textDecoration: "none",
            borderLeft: `2px solid ${active ? colors.accent : "transparent"}`,
            background: active ? colors.a[200] : "transparent",
            color: active ? colors.a[800] : colors.n[700],
            fontWeight: active
              ? typography.weight.semibold
              : typography.weight.normal,
          } as const;
          const body = (
            <>
              <Box
                component="span"
                sx={{
                  fontFamily: typography.mono,
                  fontSize: `${typography.size.fs2}px`,
                  color: active ? colors.accent : colors.n[500],
                  minWidth: collapsed ? 0 : "20px",
                }}
              >
                {num}
              </Box>
              {!collapsed && <Box component="span">{name}</Box>}
            </>
          );
          if (href === null)
            return (
              <Box
                key={item.key}
                aria-disabled="true"
                title={t("shell.navNeedsCase")}
                sx={{ ...shared, opacity: 0.45, cursor: "not-allowed" }}
              >
                {body}
              </Box>
            );
          return (
            <Box
              key={item.key}
              component={Link}
              href={href}
              aria-current={active ? "page" : undefined}
              aria-label={`${num} ${name}`}
              title={collapsed ? name : undefined}
              sx={{
                ...shared,
                "&:hover": {
                  background: `color-mix(in srgb,${colors.accent} 12%,transparent)`,
                  color: colors.text,
                },
              }}
            >
              {body}
            </Box>
          );
        })}
      </Box>
      <Box
        component="main"
        sx={{
          marginLeft: `${navWidth}px`,
          padding: `${spacing.s5}px ${spacing.s8}px ${spacing.s8}px`,
          minWidth: 0,
        }}
      >
        <Box
          sx={{
            display: "flex",
            gap: "10px",
            padding: "8px 12px",
            marginBottom: `${spacing.s5}px`,
            border: `${border.width}px solid ${colors.divider}`,
            borderRadius: `${radius.md}px`,
            background: colors.paper,
            boxShadow: shadow.sm,
            borderLeft: `${border.quoteWidth}px solid ${colors.accent}`,
            fontSize: `${typography.size.fs3}px`,
            lineHeight: 1.6,
            color: colors.n[700],
          }}
        >
          {t("shell.banner")}
        </Box>
        {children}
      </Box>
    </>
  );
}
