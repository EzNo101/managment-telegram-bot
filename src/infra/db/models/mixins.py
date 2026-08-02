from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column


@declarative_mixin
class IdMixin:
    """Mixin for adding an id column to a model."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


@declarative_mixin
class CreatedAtMixin:
    """Mixin for adding a created_at column to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


@declarative_mixin
class UpdatedAtMixin:
    """Mixin for adding an updated_at column to a model."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
