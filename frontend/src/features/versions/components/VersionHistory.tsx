"use client";
import Link from "next/link";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";
import { useVersionHistory } from "../hooks";
export function VersionHistory({
  caseId,
  versionId,
}: {
  caseId: number;
  versionId: number;
}) {
  const { t } = useTranslation();
  const history = useVersionHistory(caseId);
  return (
    <Box component="details">
      <Typography component="summary">{t("versions.history.title")}</Typography>
      {history.isLoading ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : history.isError ? (
        <Box role="alert">
          <Typography>{t("versions.loadError")}</Typography>
          <Button onClick={() => void history.refetch()}>
            {t("versions.reload")}
          </Button>
        </Box>
      ) : !history.data?.length ? (
        <Typography>{t("versions.history.empty")}</Typography>
      ) : (
        history.data.map((version) => (
          <Box
            key={version.versionId}
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: `${tokens.spacing.s3}px`,
            }}
          >
            <Button
              component={Link}
              href={`/cases/${caseId}/versions/${version.versionId}`}
              aria-current={
                version.versionId === versionId ? "page" : undefined
              }
            >
              {t("versions.history.open", { number: version.versionNo })}
            </Button>
            <Typography>{version.finalizedAt}</Typography>
            <Typography>
              {t(`versions.state.${version.currentState}`)}
            </Typography>
            {version.versionId === versionId && (
              <Typography>{t("versions.history.current")}</Typography>
            )}
          </Box>
        ))
      )}
      <Button component={Link} href={`/cases/${caseId}/intake`}>
        {t("versions.intake")}
      </Button>
    </Box>
  );
}
