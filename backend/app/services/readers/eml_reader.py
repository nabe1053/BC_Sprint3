""".eml 読取（FUNC-02）。転送・引用・追伸を分離し、本文の新旧を Date ヘッダで判定する。

この reader の「読めた単位」は本文＋添付一覧（本文パート群＋attachment 名の
列挙。document_pages ではなく email_parts に詰め替えられる）。
page_count（軽微-5・決定2）: eml にはページの概念が無いため None のまま
（Service 層でも設定しない）。

FUNC-02 の受入基準:
    - sent_at は Date ヘッダから決める（表示順・出現順で新旧を判定しない）
    - 転送メールは転送者のヘッダ（from_addr/sent_at）を採用する（転送元ではない）
    - P.S.・追伸は latest_body から分離する（postscript）
    - 転送時に転送者が付け足した注記は forward_note として分離する
    - 引用された元本文は quoted_body として分離する
    - plain/html に同一内容がある場合は本文を二重に取らない（X03）
    - HTML の外部画像・リンクは取得しない（テキスト化した本文のみを保持する）

read_status の決め方（契約1〜3。build-loop T-101 reviewer 指摘対応）:
    - 契約1: 読めた単位（本文）が0個 → unreadable。読めた単位が1つ以上あり、
      読めなかった単位（添付一覧等）がある → partial。全部読めた → success
    - 契約2: 例外を外へ投げない。unreadable/空 のどの経路でも issues を1件以上残す
    - 契約3: read_status は「本文が読めたか」だけで決める。付随情報
      （引用元の日付等）の欠落では read_status を下げない。ただし issue は必ず残す
      （issue_type は "reference_missing"。本文そのものが読めないのとは区別する）

マクロ・外部リンクを実行しない（標準ライブラリ email によるヘッダ解析・
テキスト抽出のみ。ネットワークアクセスをしない。AD-004）。
"""

from __future__ import annotations

import email
import email.message
import email.utils
import re
from datetime import datetime
from email import policy
from email.errors import MissingHeaderBodySeparatorDefect
from html.parser import HTMLParser

from app.services.readers.types import EmailPartResult, EmailReadResult, ReadIssue

_FORWARD_MARKER_RE = re.compile(
    r"^-{3,}\s*(転送メッセージ|Forwarded [Mm]essage|Original Message)\s*-{3,}$"
)
_FORWARD_HEADER_RE = re.compile(
    r"^(From|To|Date|Subject)\s*[:：]\s*(.*)$", re.IGNORECASE
)
_POSTSCRIPT_RE = re.compile(r"^\s*(P\.S\.?|追伸)", re.IGNORECASE)
_QUOTE_PREFIX_RE = re.compile(r"^\s*>\s?")
_REPLY_QUOTE_SENDER_RE = re.compile(r"<([^<>\s]+@[^<>\s]+)>")


class _TextOnlyHTMLParser(HTMLParser):
    """HTML からテキストノードのみを取り出す（属性値・外部リンクは含めない）。"""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip = True
        if tag in ("p", "br", "div", "tr"):
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def _html_to_text(html: str) -> str:
    parser = _TextOnlyHTMLParser()
    parser.feed(html)
    lines = [line.strip() for line in parser.get_text().splitlines()]
    return "\n".join(line for line in lines if line)


def _addr_only(header_value: object | None) -> str | None:
    """ヘッダ値からメールアドレスのみを取り出す（軽微-B）。

    'Name <addr>' 形式・単なる 'addr' 形式のブレを `email.utils.parseaddr` で
    統一し、常にアドレスのみを返す（アドレスとして解釈できない場合は元の
    文字列を捏造せずそのまま返す）。
    """
    if header_value is None:
        return None
    raw = str(header_value)
    _, addr = email.utils.parseaddr(raw)
    return addr or raw or None


def _extract_body_text(msg: email.message.Message) -> str | None:
    """本文テキストを取り出す。plain を優先し、無ければ html をテキスト化する。"""
    if msg.is_multipart():
        plain_part = None
        html_part = None
        for part in msg.walk():
            if part.is_multipart():
                continue
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            if part.get_content_type() == "text/plain" and plain_part is None:
                plain_part = part
            elif part.get_content_type() == "text/html" and html_part is None:
                html_part = part
        if plain_part is not None:
            return plain_part.get_content()
        if html_part is not None:
            return _html_to_text(html_part.get_content())
        return None

    content_type = msg.get_content_type()
    if content_type == "text/html":
        return _html_to_text(msg.get_content())
    if content_type == "text/plain" or content_type.startswith("text/"):
        return msg.get_content()
    return None


def _list_attachments(msg: email.message.Message) -> list[str]:
    if not msg.is_multipart():
        return []
    names: list[str] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        if part.get_content_disposition() == "attachment":
            names.append(part.get_filename() or "attachment")
    return names


def _split_quote_or_forward(
    text: str,
) -> tuple[str, str | None, str | None, dict[str, str]]:
    """本文を「上部（転送者/返信者自身の文章）」と「引用・転送された元本文」に分ける。

    戻り値: (top_text, quoted_text, marker_type, quoted_headers)。marker_type は
    "forward"（---- 転送メッセージ ---- 形式）/ "reply"（"> " 引用形式）/ None。
    quoted_headers は marker_type=="forward" のときのみ、引用ヘッダ
    （from/date/subject。キーは小文字）を持つ（重大-2: 転送元の引用ヘッダを
    捨てずに残す）。
    """
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if _FORWARD_MARKER_RE.match(line.strip()):
            top = "\n".join(lines[:i]).strip()
            rest = lines[i + 1 :]
            j = 0
            quoted_headers: dict[str, str] = {}
            while j < len(rest):
                stripped = rest[j].strip()
                if stripped == "":
                    j += 1
                    continue
                header_match = _FORWARD_HEADER_RE.match(stripped)
                if header_match is None:
                    break
                key = header_match.group(1).lower()
                value = header_match.group(2).strip()
                quoted_headers[key] = value
                j += 1
            quoted = "\n".join(rest[j:]).strip()
            return top, quoted or None, "forward", quoted_headers

    for i, line in enumerate(lines):
        if _QUOTE_PREFIX_RE.match(line):
            top = "\n".join(lines[:i]).strip()
            quoted_lines = [_QUOTE_PREFIX_RE.sub("", line_) for line_ in lines[i:]]
            quoted = "\n".join(quoted_lines).strip()
            return top, quoted or None, "reply", {}

    return text.strip(), None, None, {}


def _parse_forward_header_date(date_str: str) -> datetime | None:
    """転送元ヘッダの Date 文字列を RFC2822 として解釈する。

    和文形式（例: "2026年7月8日(水) 11:02"）等パース不能な場合は None を返す
    （日時を捏造しない。呼び出し側で issues に理由を残す）。
    """
    try:
        return email.utils.parsedate_to_datetime(date_str)
    except (TypeError, ValueError, OverflowError):
        return None


def _extract_reply_quote_sender(quoted_text: str) -> str | None:
    """ "> On ... <foo@example.com> wrote:" 形式（Apple Mail 等の返信引用）の
    先頭付近から差出人メールアドレスを推測する。日時は非定型で確実にパースできる
    保証がないため、本関数では扱わない（捏造しない）。"""
    for line in quoted_text.splitlines()[:5]:
        match = _REPLY_QUOTE_SENDER_RE.search(line)
        if match:
            # 軽微-B: ブラケット込みではなくアドレスのみを返す（他箇所と統一）。
            return match.group(1)
    return None


def _split_top_text(
    top_text: str, marker_type: str | None
) -> tuple[str, str | None, str | None]:
    """上部テキストから postscript（追伸）と forward_note（転送者の注記）を分離する。

    戻り値: (latest_body, forward_note, postscript)。
    """
    lines = top_text.splitlines()

    ps_start = None
    for i, line in enumerate(lines):
        if _POSTSCRIPT_RE.match(line):
            ps_start = i
            break

    if ps_start is not None:
        body_lines = lines[:ps_start]
        postscript = "\n".join(lines[ps_start:]).strip() or None
    else:
        body_lines = lines
        postscript = None

    if marker_type == "forward":
        note_lines = [ln for ln in body_lines if ln.lstrip().startswith("※")]
        remain_lines = [ln for ln in body_lines if not ln.lstrip().startswith("※")]
        forward_note = "\n".join(note_lines).strip() or None
        latest_body = "\n".join(remain_lines).strip()
    else:
        forward_note = None
        latest_body = "\n".join(body_lines).strip()

    return latest_body, forward_note, postscript


def _looks_like_email(msg: email.message.Message) -> bool:
    """ヘッダー/本文の区切りが検出できたか（契約1: メールでないバイト列の判定）。

    email.message_from_bytes はどんなバイト列でも例外を投げずに解釈しようと
    するため、ヘッダー区切りが見つからない `MissingHeaderBodySeparatorDefect`
    が付くケースは「メールとして解釈できていない」とみなす（中-A）。
    """
    return not any(
        isinstance(defect, MissingHeaderBodySeparatorDefect) for defect in msg.defects
    )


def read_eml(data: bytes) -> EmailReadResult:
    """.eml のバイト列からパート（latest_body/quoted_body/postscript/forward_note/
    attachment）を抽出する。

    例外を外へ投げない（契約2）。unreadable / 空 のどの経路でも issues を
    1件以上残す。
    """
    try:
        msg = email.message_from_bytes(data, policy=policy.default)
    except Exception:
        return EmailReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="メールとして解釈できない（破損データの可能性）",
                )
            ],
        )

    if not _looks_like_email(msg):
        return EmailReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail=(
                        "メール形式として認識できない"
                        "（ヘッダーと本文の区切りが見つからない）"
                    ),
                )
            ],
        )

    from_addr = _addr_only(msg["From"])
    subject = str(msg["Subject"]) if msg["Subject"] is not None else None
    date_header = msg["Date"]
    sent_at = None
    if date_header is not None:
        try:
            sent_at = date_header.datetime
        except Exception:
            sent_at = None

    try:
        raw_body = _extract_body_text(msg)
    except (LookupError, UnicodeDecodeError):
        # 未知の文字コード等、標準ライブラリのデコードに失敗するケース（中-6）。
        # pdf/xlsx reader と契約を揃え、例外を投げずに unreadable を返す。
        return EmailReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="本文の文字コードを判定できない",
                )
            ],
        )

    if raw_body is None or not raw_body.strip():
        # 契約1: 読めた単位（本文）が0個 → unreadable（空の .eml・ボディ無しを含む）。
        return EmailReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="本文テキストを取得できない（本文が空、または存在しない）",
                )
            ],
        )

    top_text, quoted_text, marker_type, quoted_headers = _split_quote_or_forward(
        raw_body
    )
    latest_body, forward_note, postscript = _split_top_text(top_text, marker_type)

    parts: list[EmailPartResult] = []
    issues: list[ReadIssue] = []
    seq = 1
    if latest_body:
        parts.append(
            EmailPartResult(
                part_role="latest_body",
                seq=seq,
                sent_at=sent_at,
                from_addr=from_addr,
                subject=subject,
                body=latest_body,
            )
        )
        seq += 1
    else:
        # 決定3: latest_body が空（転送・引用のみのメール）なら空の part を
        # 作らない。かわりに issue を残す（下流の T-203 FUNC-02 新旧判定が
        # 空文字を最新本文と誤認しないように。中-3）。
        issues.append(
            ReadIssue(
                locator=None,
                issue_type="reference_missing",
                detail="最新本文が空（転送・引用のみのメール）",
            )
        )

    if forward_note:
        parts.append(
            EmailPartResult(part_role="forward_note", seq=seq, body=forward_note)
        )
        seq += 1

    if postscript:
        parts.append(EmailPartResult(part_role="postscript", seq=seq, body=postscript))
        seq += 1

    if quoted_text:
        quoted_sent_at: datetime | None = None
        quoted_from: str | None = None
        quoted_subject: str | None = None

        if marker_type == "forward":
            # 転送メールの引用ヘッダ（重大-2）: From/Date/Subject を捨てずに残す。
            quoted_from = _addr_only(quoted_headers.get("from"))
            quoted_subject = quoted_headers.get("subject")
            date_str = quoted_headers.get("date")
            if date_str:
                quoted_sent_at = _parse_forward_header_date(date_str)
            if quoted_sent_at is None:
                # 契約3: 付随情報（引用元の日付）が読めないだけでは read_status
                # を下げない。issue_type は reference_missing（本文自体は読めて
                # いるので unreadable_page ではない。中-E・軽微-C）。
                issues.append(
                    ReadIssue(
                        locator=None,
                        issue_type="reference_missing",
                        detail=(
                            f"引用元メールの日付を解釈できない: {date_str!r}"
                            if date_str
                            else "引用元メールの日付が見つからない"
                        ),
                    )
                )
        else:
            # "> On ... <foo@example.com> wrote:" 形式（返信引用）。日時形式が
            # 非定型で確実にパースできないため、from_addr のみ best-effort で拾う。
            quoted_from = _extract_reply_quote_sender(quoted_text)
            # 中-E: 転送引用と非対称にならないよう、返信引用でも日付が
            # 取れないことを issues に残す（契約3。read_status は下げない）。
            issues.append(
                ReadIssue(
                    locator=None,
                    issue_type="reference_missing",
                    detail="引用元メールの日付は非定型形式のため解釈できない",
                )
            )

        parts.append(
            EmailPartResult(
                part_role="quoted_body",
                seq=seq,
                sent_at=quoted_sent_at,
                from_addr=quoted_from,
                subject=quoted_subject,
                body=quoted_text,
            )
        )
        seq += 1

    attachment_listing_failed = False
    try:
        attachment_names = _list_attachments(msg)
    except (LookupError, UnicodeDecodeError):
        attachment_names = []
        attachment_listing_failed = True
        issues.append(
            ReadIssue(
                locator=None,
                issue_type="reference_missing",
                detail="添付一覧の取得に失敗した（文字コード等）",
            )
        )

    for attachment_name in attachment_names:
        parts.append(
            EmailPartResult(
                part_role="attachment", seq=seq, attachment_name=attachment_name
            )
        )
        seq += 1

    # 契約1: 本文（読めた単位）はあるが、添付一覧という別の単位が読めなかった
    # 場合は partial（中-F: eml が partial を返す経路を持たせる）。
    read_status = "partial" if attachment_listing_failed else "success"

    return EmailReadResult(read_status=read_status, parts=parts, issues=issues)
