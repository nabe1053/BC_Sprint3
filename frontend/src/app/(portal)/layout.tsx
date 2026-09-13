import { AppShell } from "@/shared/ui";

export default function PortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
