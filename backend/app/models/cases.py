"""cases（A層 入力）。04-db.md 3.1。"""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class Case(TimestampedBase):
    __tablename__ = "cases"

    case_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    customer_name: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
