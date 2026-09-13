"use client";
import { useRef, useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import { useIsMutating } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";
import { createExportKey, useCreateExport } from "../hooks";
import { exportErrorKey } from "../model";

/** Blob をブラウザに保存させる。副作用があるため shared/lib には置かない。 */
function saveBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // 保存が始まる前に無効化するとダウンロードが黙って失敗する環境がある。
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function ExportButton({
  versionId,
  label,
  disabled = false,
}: {
  versionId: number;
  label: string;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const create = useCreateExport(versionId);
  // 同じ版のボタンが画面に複数あっても、進行中は全て無効にする。
  const running =
    useIsMutating({ mutationKey: createExportKey(versionId) }) > 0;
  const lock = useRef(false);
  const [saved, setSaved] = useState<{
    name: string;
    namedByServer: boolean;
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  async function run() {
    // 再描画前の連打でも二重POSTしない（再POSTは別の出力レコードを作る）。
    if (lock.current) return;
    lock.current = true;
    setError(null);
    setSaved(null);
    try {
      const result = await create.mutateAsync();
      saveBlob(result.blob, result.fileName);
      setSaved({ name: result.fileName, namedByServer: result.namedByServer });
    } catch (cause) {
      setError(cause);
    } finally {
      lock.current = false;
    }
  }
  return (
    <Box sx={{ display: "grid", gap: `${tokens.spacing.s2}px` }}>
      <Button
        variant="outlined"
        onClick={() => void run()}
        disabled={disabled || create.isPending || running}
        aria-busy={create.isPending || running}
      >
        {create.isPending || running ? t("versions.export.pending") : label}
      </Button>
      {saved && (
        <Box role="status">
          <Typography variant="body2">
            {t("versions.export.savedAs", { name: saved.name })}
          </Typography>
          {!saved.namedByServer && (
            <Typography variant="body2">
              {t("versions.export.fallbackName")}
            </Typography>
          )}
        </Box>
      )}
      {error != null && (
        <Box role="alert">
          <Typography variant="body2">{t(exportErrorKey(error))}</Typography>
        </Box>
      )}
    </Box>
  );
}
