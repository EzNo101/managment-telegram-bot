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
    amount_usd: Mapped[float] = mapped_column(nullable=False)
    method: Mapped[PaymentMethod] = mapped_column()
    status: Mapped[PaymentStatus] = mapped_column(nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
