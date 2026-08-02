from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.enums import SubscriptionStatus
from src.infra.db.base import Base
from src.infra.db.models.mixins import CreatedAtMixin, IdMixin, UpdatedAtMixin


class Subscription(Base, IdMixin, CreatedAtMixin, UpdatedAtMixin):
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        String(32),
        server_default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
