import { notFound } from "next/navigation";
import { CaseSelect } from "@/features/cases";
import { ApprovalPage } from "@/features/versions";
export default async function ApprovalRoute({
  params,
}: {
  params: Promise<{ caseId: string; versionId: string }>;
}) {
  const { caseId, versionId } = await params;
  const caseNumber = Number(caseId),
    versionNumber = Number(versionId);
  if (
    !/^\d+$/.test(caseId) ||
    !/^\d+$/.test(versionId) ||
    !Number.isSafeInteger(caseNumber) ||
    !Number.isSafeInteger(versionNumber) ||
    caseNumber <= 0 ||
    versionNumber <= 0
  )
    notFound();
  return (
    <ApprovalPage
      key={`${caseNumber}:${versionNumber}`}
      caseId={caseNumber}
      versionId={versionNumber}
      caseSwitcher={<CaseSelect caseId={caseNumber} target="approval" />}
    />
  );
}
