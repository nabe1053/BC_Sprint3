import { CaseShell } from "@/features/cases";

export default function PortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <CaseShell>{children}</CaseShell>;
}
