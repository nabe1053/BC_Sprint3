"""アプリケーション設定・環境変数管理。

Sprint 3 は認証を実装しない（CLAUDE.md 決定事項1）。JWT_SECRET_KEY 等は持たない。
接続情報・API キーは .env のみに置き、git 管理下のファイルに書かない。
"""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # アプリケーション
    APP_NAME: str = "OCTG Item List Agent API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # データベース（SQLAlchemy 2.0 AsyncSession・psycopg3 ドライバ）
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/octg_db"

    # CORS（ローカル Next.js 開発サーバーのみ許可。N02: 外部公開しない）
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Claude Agent SDK（Slice 0-7。未設定でも起動できる。実行時にチェックする）
    ANTHROPIC_API_KEY: SecretStr | None = None
    AGENT_MODE: Literal["local_dummy", "claude"] = "local_dummy"

    # ファイル入力（読取専用の原本パス。references/ 配下のみを対象にする想定。D02 の上限は別途アプリで判定）
    DOCUMENTS_ROOT: str = "../references"

    # 資料投入（#5）の保存先。05-api-ipo.md 0.4:
    # storage_path = f"{STORAGE_ROOT}/{caseId}/{uuid4}{拡張子}"。元のファイル名をパスに使わない。
    # git 管理外（.gitignore に backend/storage/ を追加済み）。
    STORAGE_ROOT: str = "storage"

    # D02（入力上限）の開発時仮値（memory.md AD-003）。初版受入前に研修者が実値を確定する（TODO-001）。
    MAX_DOCUMENTS_PER_CASE: int = 50
    MAX_FILE_SIZE_MB: int = 20
    MAX_PDF_PAGES: int = 200
    MAX_XLSX_SHEETS: int = 50


settings = Settings()
