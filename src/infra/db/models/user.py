from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base
from src.infra.db.models.mixins import CreatedAtMixin, IdMixin, UpdatedAtMixin


class User(Base, IdMixin, CreatedAtMixin, UpdatedAtMixin):
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    is_admin: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    is_banned: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
