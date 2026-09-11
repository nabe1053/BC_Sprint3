"""eml 読取（FUNC-02）の単体テスト。

期待インタフェース:
    app.services.readers.eml_reader.read_eml(data: bytes) -> EmailReadResult
    EmailReadResult:
        read_status: "success" | "partial" | "unreadable"
        parts: list[EmailPartResult]
            part_role: "latest_body" | "quoted_body" | "postscript"
                       | "forward_note" | "attachment"
            seq: int (出現順。1始まり)
            sent_at: datetime | None（Date ヘッダから。tz 情報を保持する）
            from_addr: str | None
            subject: str | None
            body: str | None
            attachment_name: str | None
        issues: list[ReadIssue]

sent_at は Date ヘッダから決める。seq（出現順）で新旧を判定しない（FUNC-02 の受入基準）。
"""

import email.message

from app.services.readers.eml_reader import read_eml


def _latest_body(result):
    return next(p for p in result.parts if p.part_role == "latest_body")


def _part(result, role):
    return next((p for p in result.parts if p.part_role == role), None)


def test_sample04_postscript_is_separated_from_latest_body(references_dir) -> None:
    """sample-04: P.S. は postscript として分離され、latest_body には含まれない。"""
    data = (references_dir / "sample-04-nanpo-sekiyu-hikiai-mail.eml").read_bytes()

    result = read_eml(data)

    assert result.read_status == "success"
    latest = _latest_body(result)
    postscript = _part(result, "postscript")

    assert postscript is not None
    assert "320本" in postscript.body
    assert "P.S." not in latest.body


def test_sample04_headers_are_extracted(references_dir) -> None:
    """sample-04: From / Date / Subject（MIME エンコード済み）が正しく取れる。"""
    data = (references_dir / "sample-04-nanpo-sekiyu-hikiai-mail.eml").read_bytes()

    result = read_eml(data)
    latest = _latest_body(result)

    assert latest.from_addr is not None
    assert "h-taguchi@nanpo-oil.example.com" in latest.from_addr
    assert latest.subject is not None
    assert "OCTG" in latest.subject
    assert latest.sent_at is not None
    assert latest.sent_at.year == 2026
    assert latest.sent_at.month == 7
    assert latest.sent_at.day == 3
    assert latest.sent_at.hour == 10
    assert latest.sent_at.minute == 24
    # tz 情報を落とさない（CLAUDE.md: timestamptz。TZ を補わない）
    assert latest.sent_at.tzinfo is not None


def test_sample07_forward_note_and_quoted_body_are_separated(references_dir) -> None:
    """sample-07: 転送者（大久保）の注記は forward_note、転送元の本文は quoted_body。"""
    data = (references_dir / "sample-07-omi-kussaku-hikiai-tenso-mail.eml").read_bytes()

    result = read_eml(data)

    latest = _latest_body(result)
    quoted = _part(result, "quoted_body")
    forward_note = _part(result, "forward_note")

    assert quoted is not None
    assert "青海掘削工業" in quoted.body or "王" in quoted.body

    assert forward_note is not None
    assert "単価はまだ不要" in forward_note.body

    # 転送者の注記は latest_body の指示文とは別レコードであること
    assert forward_note.body != latest.body


def test_sample07_headers_use_forwarder_not_original_sender(references_dir) -> None:
    """sample-07: from_addr / sent_at はトップの転送メールのヘッダから決まる
    （転送元メールの日時ではない）。"""
    data = (references_dir / "sample-07-omi-kussaku-hikiai-tenso-mail.eml").read_bytes()

    result = read_eml(data)
    latest = _latest_body(result)

    assert latest.from_addr is not None
    assert "okubo@futaba-bussan.example.com" in latest.from_addr
    assert latest.sent_at.day == 8
    assert latest.sent_at.month == 7


def test_sample10_latest_body_has_revised_quantity_quoted_has_original(
    references_dir,
) -> None:
    """sample-10: 最新本文は 300 jts（訂正後）、引用部は 240 jts（訂正前）を保持する。
    表示順（引用が下にある）ではなく Date ヘッダの新旧で latest/quoted を判定する。"""
    data = (references_dir / "sample-10-gulftex-energy-email-thread.eml").read_bytes()

    result = read_eml(data)
    latest = _latest_body(result)
    quoted = _part(result, "quoted_body")

    assert "300 jts" in latest.body
    assert quoted is not None
    assert "240 jts" in quoted.body


def test_sample10_sent_at_is_the_latest_header_not_quoted_date(references_dir) -> None:
    """sample-10: sent_at は最新本文の Date ヘッダ（7/15）であり、引用部の日付（7/14）ではない。"""
    data = (references_dir / "sample-10-gulftex-energy-email-thread.eml").read_bytes()

    result = read_eml(data)
    latest = _latest_body(result)

    assert latest.sent_at.day == 15
    assert latest.sent_at.month == 7


def test_plain_and_html_duplicate_body_is_not_extracted_twice() -> None:
    """plain と HTML に同一内容がある場合、本文を二重に取らない（X03・FUNC-02）。"""
    msg = email.message.EmailMessage()
    msg["From"] = "sender@example.com"
    msg["Subject"] = "duplicate body test"
    msg["Date"] = "Mon, 01 Sep 2026 09:00:00 +0900"
    msg.set_content("見積をお願いします。数量は100本です。")
    msg.add_alternative(
        "<html><body><p>見積をお願いします。数量は100本です。</p></body></html>",
        subtype="html",
    )
    data = msg.as_bytes()

    result = read_eml(data)

    body_parts = [p for p in result.parts if p.part_role == "latest_body"]
    assert len(body_parts) == 1
    assert result.read_status == "success"


def test_sample07_quoted_body_keeps_original_sender_metadata(references_dir) -> None:
    """sample-07: 引用部（転送元メール）のヘッダは可能な範囲で quoted_body に
    残す（reviewer 指摘 重大-2）。転送元の Date は和文形式
    （"2026年7月8日(水) 11:02"）でパース不能なため sent_at は None のまま、
    from_addr は取れる（軽微-G: 実挙動を確定値でアサートする）。"""
    data = (references_dir / "sample-07-omi-kussaku-hikiai-tenso-mail.eml").read_bytes()

    result = read_eml(data)
    quoted = _part(result, "quoted_body")

    assert quoted is not None
    assert quoted.sent_at is None
    assert quoted.from_addr == "wang.lei@qinghai-drilling.example.cn"
    assert any("日付" in i.detail or "date" in i.detail.lower() for i in result.issues)


def test_sample10_quoted_body_keeps_original_sender_metadata(references_dir) -> None:
    """sample-10: 引用部（返信元メール）は返信引用形式（"> On ... wrote:"）で
    日時が非定型のため sent_at は None、from_addr はアドレスのみで取れる
    （reviewer 指摘 重大-2・軽微-B・軽微-G）。"""
    data = (references_dir / "sample-10-gulftex-energy-email-thread.eml").read_bytes()

    result = read_eml(data)
    quoted = _part(result, "quoted_body")

    assert quoted is not None
    assert quoted.sent_at is None
    assert quoted.from_addr == "r.delgado@gulftex-energy.example.com"
    assert any("日付" in i.detail or "date" in i.detail.lower() for i in result.issues)


def test_malformed_charset_is_unreadable_not_a_crash() -> None:
    """未知の文字コードが指定された壊れた .eml は例外を投げず read_status=unreadable
    として返す（reviewer 指摘 中-6: pdf/xlsx と契約を揃える）。"""
    raw = (
        b"From: a@example.com\r\n"
        b"To: b@example.com\r\n"
        b"Subject: test\r\n"
        b"Date: Mon, 01 Sep 2026 09:00:00 +0900\r\n"
        b'Content-Type: text/plain; charset="no-such-charset"\r\n'
        b"Content-Transfer-Encoding: 8bit\r\n"
        b"\r\n"
        b"hello\r\n"
    )

    result = read_eml(raw)

    assert result.read_status == "unreadable"
    assert len(result.issues) == 1


def test_empty_eml_is_unreadable_with_issue() -> None:
    """空の .eml（0バイト）は読める単位が0個のため unreadable（契約1・中-A）。
    例外を投げず issue を1件以上残す（契約2）。"""
    result = read_eml(b"")

    assert result.read_status == "unreadable"
    assert len(result.issues) >= 1
    assert result.issues[0].locator is None
    assert result.issues[0].detail


def test_non_email_bytes_is_unreadable_with_issue() -> None:
    """メールでないバイト列（ヘッダー/本文の区切りが無い）は unreadable
    （契約1・中-A）。例外を投げず issue を残す（契約2）。"""
    data = (
        b"this is not an email at all, just random text\n"
        b"with multiple lines\nand no headers"
    )

    result = read_eml(data)

    assert result.read_status == "unreadable"
    assert len(result.issues) >= 1
    assert result.issues[0].locator is None
    assert result.issues[0].detail


def test_email_with_no_body_is_unreadable_with_issue() -> None:
    """ヘッダーはあるがボディが無い（空文字）メールは unreadable（契約1）。"""
    msg = email.message.EmailMessage()
    msg["From"] = "sender@example.com"
    msg["Subject"] = "no body"
    msg["Date"] = "Mon, 01 Sep 2026 09:00:00 +0900"
    msg.set_content("")
    data = msg.as_bytes()

    result = read_eml(data)

    assert result.read_status == "unreadable"
    assert len(result.issues) >= 1


def test_empty_latest_body_part_is_not_created_when_forward_or_quote_only() -> None:
    """決定3（中-3）: 本文が転送・引用のみで latest_body が空になる場合、
    空の latest_body part は作らず、reference_missing issue を残す。"""
    msg = email.message.EmailMessage()
    msg["From"] = "sender@example.com"
    msg["Subject"] = "quote only"
    msg["Date"] = "Mon, 01 Sep 2026 09:00:00 +0900"
    msg.set_content("> quoted line 1\n> quoted line 2")
    data = msg.as_bytes()

    result = read_eml(data)

    assert _part(result, "latest_body") is None
    quoted = _part(result, "quoted_body")
    assert quoted is not None
    assert "quoted line 1" in quoted.body
    assert any(
        i.issue_type == "reference_missing"
        and i.locator is None
        and "最新本文が空" in i.detail
        for i in result.issues
    )


def test_attachment_listing_failure_is_partial_not_success(monkeypatch) -> None:
    """中-F: 本文（読めた単位）はあるが添付一覧（別の単位）が読めない場合は
    partial（success にも unreadable にもしない。契約1）。issue も残す
    （契約2・軽微-C: issue_type は reference_missing）。"""
    from app.services.readers import eml_reader as module

    def _raise_lookup_error(msg):
        raise LookupError("attachment enumeration failed")

    monkeypatch.setattr(module, "_list_attachments", _raise_lookup_error)

    msg = email.message.EmailMessage()
    msg["From"] = "sender@example.com"
    msg["Subject"] = "with attachment issue"
    msg["Date"] = "Mon, 01 Sep 2026 09:00:00 +0900"
    msg.set_content("本文はここに書かれています。")
    data = msg.as_bytes()

    result = module.read_eml(data)

    assert result.read_status == "partial"
    assert any(i.issue_type == "reference_missing" for i in result.issues)


def test_message_parse_failure_leaves_an_issue(monkeypatch) -> None:
    """中-B: メッセージ解析そのものが失敗する経路でも issue を残す
    （契約2。この経路だけ issue が空、という非対称を無くす）。"""
    from app.services.readers import eml_reader as module

    def _raise(data, policy=None):
        raise ValueError("boom")

    monkeypatch.setattr(module.email, "message_from_bytes", _raise)

    result = module.read_eml(b"whatever")

    assert result.read_status == "unreadable"
    assert len(result.issues) >= 1
    assert result.issues[0].detail


def test_top_level_from_addr_is_address_only_not_display_name(references_dir) -> None:
    """軽微-B: from_addr は 'Name <addr>' 形式のままではなく、
    `email.utils.parseaddr` でアドレスのみに統一する。"""
    data = (references_dir / "sample-04-nanpo-sekiyu-hikiai-mail.eml").read_bytes()

    result = read_eml(data)
    latest = _latest_body(result)

    assert latest.from_addr == "h-taguchi@nanpo-oil.example.com"


def test_html_only_body_is_read_without_external_resources() -> None:
    """HTML のみの本文でも本文は読み取るが、外部画像・リンクは取得しない
    （テキスト化した本文のみが body に入り、img タグの src 等は含まれない）。"""
    msg = email.message.EmailMessage()
    msg["From"] = "sender@example.com"
    msg["Subject"] = "html only body"
    msg["Date"] = "Mon, 01 Sep 2026 09:00:00 +0900"
    msg.add_alternative(
        "<html><body><p>本文のみです。</p>"
        '<img src="https://external.example.com/tracker.png"></body></html>',
        subtype="html",
    )
    data = msg.as_bytes()

    result = read_eml(data)
    latest = _latest_body(result)

    assert "本文のみです" in latest.body
    assert "external.example.com" not in latest.body
