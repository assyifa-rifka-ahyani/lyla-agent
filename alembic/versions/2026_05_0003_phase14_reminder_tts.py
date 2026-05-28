"""phase14 reminder tts state

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.add_column(sa.Column("tts_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("tts_audio_id", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("tts_synthesized_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.drop_column("tts_synthesized_at")
        batch_op.drop_column("tts_audio_id")
        batch_op.drop_column("tts_status")
