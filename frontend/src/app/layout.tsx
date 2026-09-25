import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "引合書整理エージェント",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
