from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base
from src.infra.db.models.mixins import CreatedAtMixin, IdMixin, UpdatedAtMixin


class Plan(Base, IdMixin, CreatedAtMixin, UpdatedAtMixin):
    price_usd: Mapped[int] = mapped_column(nullable=False)  # in cents
    duration_days: Mapped[int] = mapped_column(nullable=False)
