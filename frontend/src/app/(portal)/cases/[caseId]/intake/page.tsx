import { notFound } from "next/navigation";
import { IntakePage } from "@/features/documents";
export default async function IntakeRoute({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  const id = Number(caseId);
  if (!/^\d+$/.test(caseId) || !Number.isSafeInteger(id) || id <= 0) notFound();
  return <IntakePage key={id} caseId={id} />;
}
