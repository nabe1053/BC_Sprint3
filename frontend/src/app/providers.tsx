"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { AppRouterCacheProvider } from "@mui/material-nextjs/v15-appRouter";
import { muiColor } from "@/shared/theme/mui-color";
import { tokens } from "@/shared/theme/tokens";
import "@/shared/i18n";

// 脱・標準MUI の必須設定（.claude/rules/design-guidelines.md 参照）。
// MUI 既定のブランドカラー・Roboto・大文字ボタンを残さない（トークン由来の色のみ使う）。
const { colors, typography, spacing, radius, shadow, border } = tokens;

const theme = createTheme({
  palette: {
    // 鋼色アクセント1色相＋状態色3（03-spec 3章）。MUI 既定のブランドカラーは残さない。
    primary: {
      light: colors.a[300],
      main: colors.accent,
      dark: colors.a[800],
      contrastText: colors.onDark,
    },
    secondary: { main: colors.n[700] },
    // MUI v5はoklchの文字色を自動計算できないため、既存トークンでcontrastTextも明示。
    // 状態色は文字ラベルの補助にのみ使う（03-spec 運用原則2）。装飾に使わない。
    error: {
      main: colors.danger.main,
      light: colors.danger[100],
      dark: colors.danger[800],
      contrastText: colors.onDark,
    },
    warning: {
      main: colors.warn.main,
      light: colors.warn[100],
      dark: colors.warn[800],
      contrastText: colors.onDark,
    },
    success: {
      main: colors.ok.main,
      light: colors.ok[100],
      dark: colors.ok[800],
      contrastText: colors.onDark,
    },
    divider: muiColor(colors.divider),
    background: { default: colors.bg, paper: colors.paper },
    text: { primary: colors.text, secondary: colors.n[500] },
  },
  typography: {
    fontFamily: typography.body,
    // ルートは実寸の基準（rem の基準ではない）。以下は px 指定で 03-spec の6段に対応させる。
    fontSize: typography.root,
    htmlFontSize: typography.root,
    fontWeightRegular: typography.weight.normal,
    fontWeightMedium: typography.weight.medium,
    fontWeightBold: typography.weight.semibold,
    h1: {
      fontSize: typography.size.fs6,
      fontWeight: typography.weight.semibold,
      letterSpacing: typography.letterSpacing.tight,
    },
    h2: {
      fontSize: typography.size.fs5,
      fontWeight: typography.weight.semibold,
    },
    h3: {
      fontSize: typography.size.fs5,
      fontWeight: typography.weight.semibold,
    },
    body1: { fontSize: typography.size.fs4 },
    body2: { fontSize: typography.size.fs3 },
    caption: { fontSize: typography.size.fs2 },
    overline: {
      fontFamily: typography.mono,
      fontSize: typography.size.fs1,
      letterSpacing: typography.letterSpacing.caps,
      textTransform: "none",
    },
    button: { fontSize: typography.size.fs4, textTransform: "none" },
  },
  // MUI の spacing(n) を 4px グリッドに合わせる（spacing(1)=4px … spacing(8)=32px）。
  // 03-spec の s1–s8（s7 欠番）に対応。欠番の 28px を作らないため、値は tokens.spacing から引くこと。
  spacing: (factor: number) => `${factor * spacing.s1}px`,
  shape: { borderRadius: radius.md },
  shadows: [
    "none",
    shadow.sm,
    shadow.sm,
    shadow.md,
    shadow.md,
    ...Array<string>(20).fill(shadow.lg),
  ] as unknown as ReturnType<typeof createTheme>["shadows"],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          lineHeight: typography.lineHeight,
          fontFeatureSettings: typography.fontFeatureSettings,
          letterSpacing: typography.letterSpacing.tight,
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true, variant: "outlined" },
      styleOverrides: {
        // モックの button: 透明地・ヘアライン枠・7px 12px。
        root: {
          textTransform: "none",
          borderRadius: radius.md,
          padding: "7px 12px",
          fontWeight: typography.weight.medium,
          lineHeight: 1.2,
          whiteSpace: "nowrap",
          minWidth: 0,
        },
        outlined: {
          borderColor: colors.divider,
          color: colors.text,
          backgroundColor: "transparent",
          "&:hover": {
            borderColor: colors.divider,
            backgroundColor: `color-mix(in srgb,${colors.text} 7%,transparent)`,
          },
        },
        // モックの .primary: 鋼色地＋角のレジストレーションマーク。
        contained: {
          position: "relative",
          boxShadow: shadow.sm,
          "&:hover": { backgroundColor: colors.a[600] },
          "&:active": { backgroundColor: colors.a[700] },
          "&::before,&::after": {
            content: '""',
            position: "absolute",
            width: "9px",
            height: "9px",
            pointerEvents: "none",
            background:
              "linear-gradient(currentColor,currentColor) center/1px 100% no-repeat,linear-gradient(currentColor,currentColor) center/100% 1px no-repeat",
            color: `color-mix(in srgb,${colors.text} 55%,transparent)`,
          },
          "&::before": { top: "-5px", left: "-5px" },
          "&::after": { bottom: "-5px", right: "-5px" },
        },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: { root: { borderRadius: radius.lg } },
    },
    MuiCard: {
      defaultProps: { variant: "outlined" },
      styleOverrides: {
        root: { borderRadius: radius.lg, boxShadow: shadow.sm },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: radius.sm, fontSize: typography.size.fs2 },
      },
    },
    MuiTable: {
      styleOverrides: {
        root: { fontSize: typography.size.fs4, whiteSpace: "nowrap" },
      },
    },
    MuiTableBody: {
      styleOverrides: {
        root: {
          "& tr:hover": {
            backgroundColor: `color-mix(in srgb,${colors.accent} 6%,transparent)`,
          },
          "& tr:last-child td": { borderBottom: 0 },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `${border.width}px solid ${colors.hair}`,
          fontSize: typography.size.fs4,
          padding: `10px ${spacing.s2}px`,
          verticalAlign: "top",
        },
        // モックの th: a100 の帯に小さな大文字。縦スクロールで固定する。
        head: {
          position: "sticky",
          top: 0,
          fontSize: typography.size.fs1,
          fontWeight: typography.weight.medium,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: colors.a[800],
          backgroundColor: colors.a[100],
          borderBottom: `${border.width}px solid ${colors.a[300]}`,
          whiteSpace: "nowrap",
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: radius.md, backgroundColor: colors.surface },
      },
    },
  },
});

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false },
          mutations: { retry: false },
        },
      }),
  );

  return (
    <AppRouterCacheProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </QueryClientProvider>
    </AppRouterCacheProvider>
  );
}
