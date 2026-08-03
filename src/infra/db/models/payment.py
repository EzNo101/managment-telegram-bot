from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.enums import PaymentMethod, PaymentStatus
from src.infra.db.base import Base
from src.infra.db.models.mixins import CreatedAtMixin, IdMixin, UpdatedAtMixin


class Payment(Base, IdMixin, CreatedAtMixin, UpdatedAtMixin):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"),
        nullable=False,
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscription.id"),
        nullable=True,
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.id"), nullable=False)
    amount_usd: Mapped[int] = mapped_column(nullable=False)  # in cents
    method: Mapped[PaymentMethod] = mapped_column(String(32), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        String(32),
        nullable=False,
        server_default=PaymentStatus.PENDING,
    )
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
