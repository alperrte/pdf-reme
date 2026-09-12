from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from pdf_reme.infrastructure.database.base import Base

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    stored_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    original_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    library_section: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    generation_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    last_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )
    source_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("documents.id"),
        nullable=True,
    )
    
    trashed_from_path: Mapped[str | None] = mapped_column(
    String,
    nullable=True,
)