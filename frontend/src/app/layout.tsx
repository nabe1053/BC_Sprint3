import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "OCTG Item List Agent",
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
