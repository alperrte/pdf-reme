"""create documents table

Revision ID: aee933ba08ce
Revises: 
Create Date: 2026-09-09 21:42:16.922540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aee933ba08ce'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("original_path", sa.String(length=500), nullable=True),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("library_section", sa.String(length=50), nullable=False),
        sa.Column("generation_type", sa.String(length=50), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.Column("last_opened_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),

        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_documents_sha256",
        "documents",
        ["sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_sha256",
        table_name="documents",
    )

    op.drop_table("documents")
