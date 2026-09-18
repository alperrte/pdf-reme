from datetime import datetime

from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.presentation.i18n import get_language_manager


# document_type -> (qtawesome ikonu, tema aksan rengi)
# Kartlar, satırlar ve filtre çipleri aynı eşlemeyi kullanır.
TYPE_ICON_MAP: dict[str, tuple[str, str]] = {
    "pdf": ("fa5s.file-pdf", "red"),
    "word": ("fa5s.file-word", "blue"),
    "powerpoint": ("fa5s.file-powerpoint", "orange"),
    "excel": ("fa5s.file-excel", "green"),
    "image": ("fa5s.file-image", "sky"),
}

DEFAULT_TYPE_ICON = ("fa5s.file", "blue")


def type_icon(
    document_type: str | None,
) -> tuple[str, str]:
    return TYPE_ICON_MAP.get(document_type or "", DEFAULT_TYPE_ICON)


def format_file_size(
    size_bytes: int,
) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    return f"{max(size_bytes, 0) / 1024:.0f} KB"


def format_document_meta(
    document: Document,
    *,
    date: datetime | None,
) -> str:
    language_manager = get_language_manager()

    parts: list[str] = []

    if document.page_count:
        parts.append(
            language_manager.tr(
                "document.meta.pages"
            ).format(
                count=document.page_count
            )
        )

    parts.append(
        format_file_size(
            document.file_size
        )
    )

    if date is not None:
        parts.append(
            date.strftime(
                "%d.%m.%Y"
            )
        )

    return "  •  ".join(parts)
