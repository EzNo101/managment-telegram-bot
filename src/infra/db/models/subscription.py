from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base
from src.infra.db.models.mixins import CreatedAtMixin, IdMixin, UpdatedAtMixin


class Subscription(Base, IdMixin, CreatedAtMixin, UpdatedAtMixin):
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"), nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
