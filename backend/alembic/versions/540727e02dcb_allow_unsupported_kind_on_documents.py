"""allow unsupported kind on documents

`documents.kind` の CHECK に 'unsupported' を追加する。未対応形式（.pptx 等）を投入した事実を
資料一覧に残すため（②FUNC-01 X01「同一資料の二重投入・未対応形式でも投入の事実は残す」・
④04-db.md 3.1 documents）。この行は read_status も 'unsupported' で、document_pages は作らない。

Revision ID: 540727e02dcb
Revises: bc31bdc005d7
Create Date: 2026-09-11 23:48:10.667499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '540727e02dcb'
down_revision: Union[str, None] = 'bc31bdc005d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_documents_kind", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_kind",
        "documents",
        "kind IN ('pdf','xlsx','eml','text','unsupported')",
    )


def downgrade() -> None:
    # 注意（reviewer 指摘 軽微-1・不可逆性）: この downgrade は CHECK 制約を
    # 元に戻すだけで、既存データは一切削除しない。'unsupported' の kind/read_status
    # を持つ行が既に存在する場合、この CHECK 制約の復元は失敗する
    # （制約違反になるため）。データを勝手に消して帳尻を合わせることはしない。
    # downgrade する場合は、該当行の扱いを人手で判断してから実行すること。
    op.drop_constraint("ck_documents_kind", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_kind",
        "documents",
        "kind IN ('pdf','xlsx','eml','text')",
    )
