"""Business Logic 層のドメイン例外。

05-api-ipo.md 6章のエラーコード一覧が SSOT。ここで定義する `code` はそのまま
Presentation 層（T-102 の API 層）で `app.api.errors.ApiError` に変換される想定。
Service/Repository はこのファイルの例外だけを送出し、`app.api.*` を import しない
（clean-architecture.md: 内側は外側を知らない）。
"""

from typing import Any


class DomainError(Exception):
    """業務エラーの基底クラス。`code` は 05-api-ipo.md 6章のエラーコード。"""

    code: str = "E_DOMAIN_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.details = details or {}
        super().__init__(message)


class DuplicateCaseCodeError(DomainError):
    """案件ID（case_code）の重複。05-api-ipo.md 6章 `E_DUPLICATE_CASE_CODE`。

    根拠: 04-db.md ④ `cases.case_code` UNIQUE。
    """

    code = "E_DUPLICATE_CASE_CODE"


class UnsupportedFormatError(DomainError):
    """未対応形式（拡張子が pdf/xlsx/eml/text のいずれでもない）。

    05-api-ipo.md 5章 #5・6章 `E_UNSUPPORTED_FORMAT`。投入の事実は
    `documents`（kind='unsupported' / read_status='unsupported'）に1行残した
    うえで送出する（413 の `LimitExceededError` とは異なり記録を残す）。
    details には保存済み資料の `documentId` を入れる
    （details={"documentId": <int>}）。
    """

    code = "E_UNSUPPORTED_FORMAT"


class LimitExceededError(DomainError):
    """入力上限（D02）超過。05-api-ipo.md 6章 `E_LIMIT_EXCEEDED`。

    details は {"limit": "document_count"|"file_size"|"pdf_pages"|"xlsx_sheets",
    "max": <上限値>, "actual": <実際値>} の形に統一する（X09・AE05b: 具体的な
    超過内容を返す）。
    """

    code = "E_LIMIT_EXCEEDED"
