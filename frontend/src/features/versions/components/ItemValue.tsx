"use client";
import { Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type {
  ItemCurrentResponse,
  ItemEditRecord,
} from "@/shared/api/generated/model";
import { previousValue, valueLabelKey, type EditableField } from "../model";
export function ItemValue({
  value,
  state,
  history = [],
  field,
}: {
  value?: string | null;
  state?: string | null;
  history?: ItemEditRecord[];
  field?: EditableField;
}) {
  const { t } = useTranslation();
  const key = valueLabelKey(state);
  return (
    <>
      <Typography component="span">
        {key ? t(key) : (value ?? t("versions.values.empty"))}
      </Typography>
      <PreviousValue history={history} field={field} />
    </>
  );
}

function PreviousValue({
  history = [],
  field,
}: {
  history?: ItemEditRecord[];
  field?: EditableField;
}) {
  const { t } = useTranslation();
  const old = field ? previousValue(history, field) : null;
  const oldKey = old ? valueLabelKey(old.state) : null;
  return old ? (
    <Typography variant="caption" component="div">
      {t("versions.oldValue", {
        value: oldKey ? t(oldKey) : (old.value ?? t("versions.values.empty")),
      })}
    </Typography>
  ) : null;
}

export function DimensionValue({
  item,
  dimension,
}: {
  item: ItemCurrentResponse;
  dimension: "od" | "weight" | "wall";
}) {
  const { t } = useTranslation();
  const value = item[`${dimension}Value`] ?? t("versions.values.empty");
  const unit = item[`${dimension}Unit`] ?? t("versions.values.empty");
  return (
    <>
      <ItemValue value={`${value} ${unit}`} state={item[`${dimension}State`]} />
      <PreviousValue history={item.history} field={`${dimension}_value`} />
      <PreviousValue history={item.history} field={`${dimension}_unit`} />
    </>
  );
}
