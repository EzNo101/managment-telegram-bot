"""widen payment.pay_url to Text

Revision ID: f7c2a90e5b41
Revises: 849c8c86bdb2
Create Date: 2026-08-06 17:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7c2a90e5b41"
down_revision: Union[str, Sequence[str], None] = "849c8c86bdb2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "payment",
        "pay_url",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "payment",
        "pay_url",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
