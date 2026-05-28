"""phase14b reminder failure reason and command expiry

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.add_column(sa.Column("failure_reason", sa.String(), nullable=True))

    with op.batch_alter_table("device_commands") as batch_op:
        batch_op.add_column(
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("device_commands") as batch_op:
        batch_op.drop_column("expires_at")

    with op.batch_alter_table("reminders") as batch_op:
        batch_op.drop_column("failure_reason")
