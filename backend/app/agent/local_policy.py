"""Local dummy decisions for explicit synthetic rows; no remote model or oracle.

This deliberately does not pretend to interpret arbitrary business documents.
Unknown text/cells are reported and stop the run before publishing a draft.
Explicit URL notes are preserved as questions, never followed as instructions.
"""
import re

from app.domain.agent_types import LocalPolicyStop, ToolCall

ROW = re.compile(
    r"No\.(?P<no>[1-9][0-9]*) \| Kind: (?P<kind>casing|tubing) \| Qty: (?P<qty>(?:[0-9]+(?:\.[0-9]+)? [A-Za-z]+)|TBA|not applicable)"
)
URL_NOTE = re.compile(r"(?:注記:|Note:).*https?://", re.IGNORECASE)


async def local_dummy_policy(context):
    yield ToolCall("get_rules")
    reply = yield ToolCall("list_case_documents")
    documents = reply.data["documents"]
    sources = []
    url_notes = []
    readable = 0
    unsupported = False
    for document in documents:
        document_id = document["document_id"]
        email = document["kind"] == "eml"
        reply = yield ToolCall(
            "read_email" if email else "read_document", {"document_id": document_id}
        )
        if email:
            parts = reply.data["parts"]
            # Email revision/attachment interpretation is not a dummy capability.
            unsupported |= any(
                p["part_role"] != "latest_body"
                or p.get("subject")
                or p.get("from_addr")
                for p in parts
            )
            ranges = [
                {"locator": p["locator"], "text": p["body"], "cells": None}
                for p in parts
            ]
        else:
            ranges = reply.data["pages"]
        if not ranges:
            yield ToolCall(
                "report_unreadable",
                {
                    "document_id": document_id,
                    "locator": None,
                    "issue_type": "unreadable_page",
                    "detail": "読取可能な範囲がありません",
                },
            )
        for part in ranges:
            body = (part["text"] or "").strip()
            if not body and not part.get("cells"):
                yield ToolCall(
                    "report_unreadable",
                    {
                        "document_id": document_id,
                        "locator": part["locator"],
                        "issue_type": "unreadable_page",
                        "detail": "読取可能な本文がありません",
                    },
                )
                continue
            readable += 1
            matches = []
            notes_here = []
            for line in body.splitlines():
                if not line.strip():
                    continue
                if URL_NOTE.match(line.strip()):
                    notes_here.append((document_id, part["locator"], line))
                else:
                    matches.append((line, ROW.fullmatch(line.strip())))
            url_notes.extend(notes_here)
            if (
                part.get("cells")
                or (not matches and not notes_here)
                or any(match is None for _, match in matches)
            ):
                unsupported = True
                yield ToolCall(
                    "report_unreadable",
                    {
                        "document_id": document_id,
                        "locator": part["locator"],
                        "issue_type": "not_scanned",
                        "detail": "ローカルダミーでは明細を解釈できない範囲です",
                    },
                )
                continue
            sources.extend(
                (document_id, part["locator"], line, match.groupdict())
                for line, match in matches
            )
    if not readable:
        raise LocalPolicyStop("no_readable_document")
    if unsupported or not sources:
        yield ToolCall(
            "record_question",
            {
                "question": {
                    "question_code": "LOCAL-UNSUPPORTED",
                    "target_field": "items",
                    "reason": "ローカルダミーの対応範囲外のため明細を確定できません",
                }
            },
        )
        raise LocalPolicyStop("local_dummy_unsupported")

    yield ToolCall(
        "record_case_header",
        {
            "header": {
                "inquiry_no_state": "not_stated",
                "customer_name_state": "not_stated",
                "due_state": "not_stated",
                "place_state": "not_stated",
                "incoterms_state": "not_stated",
                "quote_deadline_tz_state": "missing",
            }
        },
    )
    rows = []
    for seq, (_, _, _, values) in enumerate(sources, 1):
        qty = values["qty"]
        numeric = qty not in ("TBA", "not applicable")
        row = {
            "row_code": str(seq),
            "source_no": values["no"],
            "seq": seq,
            "kind": values["kind"],
            "kind_raw": values["kind"],
            "grade_raw": "記載なし",
            "qty_raw": qty,
            "qty_state": "numeric"
            if numeric
            else ("tba" if qty == "TBA" else "not_applicable"),
            **{
                field + "_state": "not_stated"
                for field in (
                    "od",
                    "wall",
                    "weight",
                    "grade",
                    "connection",
                    "length",
                    "due",
                    "place",
                )
            },
        }
        if numeric:
            row["qty_value"], row["qty_unit"] = qty.split(" ", 1)
        rows.append(row)
    reply = yield ToolCall("propose_items", {"rows": rows})
    created = reply.data["items"]
    entries = []
    for seq, (item, source) in enumerate(zip(created, sources, strict=True), 1):
        document_id, locator, line, values = source
        for field in ("kind", "qty"):
            yield ToolCall(
                "record_evidence",
                {
                    "evidence": {
                        "item_id": item["item_id"],
                        "field": field,
                        "raw_value": values[field],
                        "adopted_value": values[field],
                        "document_id": document_id,
                        "locator": locator,
                        "quote": line,
                    }
                },
            )
        if values["qty"] == "TBA":
            yield ToolCall(
                "record_question",
                {
                    "question": {
                        "question_code": f"Q-{seq}",
                        "item_id": item["item_id"],
                        "target_field": "qty",
                        "reason": "数量はTBAと明記されています",
                        "category": "unknown",
                    }
                },
            )
        entries.append(
            {
                "document_id": document_id,
                "position": locator,
                "source_no": values["no"],
                "seq": seq,
                "excerpt": line,
                "status": "mapped",
                "item_ids": [item["item_id"]],
            }
        )
    for document_id, locator, line in url_notes:
        seq = len(entries) + 1
        yield ToolCall(
            "record_question",
            {
                "question": {
                    "question_code": f"URL-{seq}",
                    "target_field": "source",
                    "reason": line,
                    "category": "reference_missing",
                }
            },
        )
        entries.append(
            {
                "document_id": document_id,
                "position": locator,
                "seq": seq,
                "excerpt": line,
                "status": "excluded",
                "basis": "URLを含む注記であり明細行ではありません。取得・送信は実行していません。",
            }
        )
    yield ToolCall("record_source_inventory", {"entries": entries})
    reply = yield ToolCall("validate_draft")
    if reply.data["violations"]:
        raise LocalPolicyStop("validation_unresolved")
    yield ToolCall("finalize_draft")
