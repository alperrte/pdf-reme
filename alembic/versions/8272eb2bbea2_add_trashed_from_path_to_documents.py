"""add trashed_from_path to documents

Revision ID: 8272eb2bbea2
Revises: aee933ba08ce
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8272eb2bbea2"
down_revision: Union[str, Sequence[str], None] = "aee933ba08ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "trashed_from_path",
                sa.String(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column(
            "trashed_from_path"
        )