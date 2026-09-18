import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pdf_reme.application.services.import_document_service import (
    ImportDocumentService,
)
from pdf_reme.application.services.library_service import LibraryService
from pdf_reme.application.services.trash_service import TrashService
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.database.session import session_scope
from pdf_reme.infrastructure.filesystem.file_hash import calculate_sha256
from pdf_reme.infrastructure.filesystem.file_validation import (
    SUPPORTED_EXTENSIONS,
)
from pdf_reme.infrastructure.filesystem.trash_file_manager import (
    TrashFileManager,
)
from pdf_reme.shared.paths.app_paths import AppPaths


# Presentation katmanının application/infrastructure servislerine
# tek giriş noktası. Her sayfa kendi session_scope()/repository/
# servis kurulum tekrarını yazmasın diye burada toplandı. session_scope()
# çıkışta commit eder; SQLAlchemy'nin varsayılan expire_on_commit=True
# davranışı yüzünden commit sonrası tüm alanlar "expired" olur ve session
# kapandıktan sonra (sayfalar Document alanlarını okurken) DetachedInstanceError
# fırlatır. Bunu infrastructure/session.py'a dokunmadan, sadece bu presentation
# katmanı dosyasında, session bazında expire_on_commit=False ayarlayarak çözüyoruz.
@contextmanager
def _scope():
    with session_scope() as session:
        session.expire_on_commit = False
        yield session


def _library_service(session) -> LibraryService:
    return LibraryService(
        SQLAlchemyDocumentRepository(session)
    )


def _trash_service(session) -> TrashService:
    return TrashService(
        SQLAlchemyDocumentRepository(session),
        TrashFileManager(AppPaths()),
    )


def _sort_by_created_at_desc(
    documents: list[Document],
) -> list[Document]:
    # Belgeleri en son eklenen en üstte olacak şekilde sıralar.
    # LibraryService'in filtre metotları (get_uploaded_documents vb.)
    # kendi çıktısını sıralamıyor; repository.get_all() SQL tarafında
    # created_at DESC ile sıralasa da, eşit created_at değerlerinde
    # (toplu içe aktarımdan gelen belgeler gibi) veritabanı motoru
    # kararlı bir sıra garanti etmez. Bu da örn. bir belge favoriye
    # eklenip liste yenilendiğinde kartın listede yer değiştirmesi
    # gibi kullanıcıyı şaşırtan bir davranışa yol açar. id'yi ikincil
    # anahtar olarak kullanmak, her `refresh()` çağrısında aynı sırayı
    # garanti eder.
    return sorted(
        documents,
        key=lambda document: (document.created_at, document.id),
        reverse=True,
    )


def fetch_library_documents() -> list[Document]:
    with _scope() as session:
        service = _library_service(session)

        documents = (
            service.get_uploaded_documents()
            + service.get_generated_documents()
        )

        return _sort_by_created_at_desc(documents)


# Favori sırası: Document modelinde "favoriye eklenme zamanı" alanı yok
# (application/infrastructure salt-okunur). "En son favorilenen en üstte"
# davranışı için, belge id -> artan sıra numarası eşlemesini uygulama
# veri klasöründeki küçük bir JSON dosyasında tutuyoruz. Kaydı olmayan
# (bu özellikten önce favorilenmiş) belgeler listenin altında, kendi
# aralarında created_at'e göre sıralanır.
def _favorite_order_file():
    return AppPaths().data_dir / "favorite_order.json"


def _load_favorite_order() -> dict[str, int]:
    try:
        raw = json.loads(
            _favorite_order_file().read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return {}

    if not isinstance(raw, dict):
        return {}

    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, int)
    }


def _save_favorite_order(order: dict[str, int]) -> None:
    path = _favorite_order_file()

    try:
        temp_path = path.with_suffix(".json.part")
        temp_path.write_text(json.dumps(order), encoding="utf-8")
        temp_path.replace(path)
    except OSError:
        # Sıra bilgisi kozmetik; yazılamazsa favori işlemi başarısız olmasın.
        pass


def _record_favorite_state(
    document_id: str,
    is_favorite: bool,
) -> None:
    order = _load_favorite_order()

    if is_favorite:
        order[document_id] = max(order.values(), default=0) + 1
    else:
        order.pop(document_id, None)

    _save_favorite_order(order)


def fetch_favorites() -> list[Document]:
    with _scope() as session:
        documents = _library_service(session).get_favorites()

    order = _load_favorite_order()

    return sorted(
        documents,
        key=lambda document: (
            order.get(document.id, 0),
            document.created_at,
            document.id,
        ),
        reverse=True,
    )


def fetch_recent(
    limit: int = 50,
) -> list[Document]:
    with _scope() as session:
        return _library_service(session).get_recent_documents(
            limit=limit
        )


def fetch_trashed() -> list[Document]:
    with _scope() as session:
        return _trash_service(session).get_trashed_documents()


def toggle_favorite(
    document_id: str,
) -> Document:
    with _scope() as session:
        document = _library_service(session).toggle_favorite(
            document_id
        )

    _record_favorite_state(document.id, document.is_favorite)

    return document


def set_favorite(
    document_id: str,
    value: bool,
) -> Document:
    with _scope() as session:
        service = _library_service(session)

        document = service.repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Belge bulunamadı.")

        if document.is_favorite != value:
            document = service.toggle_favorite(document_id)

    _record_favorite_state(document.id, document.is_favorite)

    return document


def mark_as_opened(
    document_id: str,
) -> Document:
    with _scope() as session:
        return _library_service(session).mark_as_opened(
            document_id
        )


def move_to_trash(
    document_id: str,
) -> Document:
    with _scope() as session:
        return _trash_service(session).move_to_trash(
            document_id
        )


def restore_from_trash(
    document_id: str,
) -> Document:
    with _scope() as session:
        return _trash_service(session).restore(
            document_id
        )


def permanently_delete(
    document_id: str,
) -> None:
    with _scope() as session:
        _trash_service(session).permanently_delete(
            document_id
        )


def clear_trash() -> int:
    with _scope() as session:
        return _trash_service(session).clear_trash()


@dataclass(frozen=True)
class ImportOutcome:
    """Tek bir dosyanın içe aktarma sonucu (sunum katmanı için)."""

    path: str
    status: str  # "imported" | "duplicate" | "failed"
    reason: str | None = None
    existing_name: str | None = None
    existing_trashed: bool = False


# Alt katmanların döndürdüğü hata metinleri -> sunum katmanı neden kodları.
_ERROR_REASONS = {
    "Dosya bulunamadı.": "not_found",
    "Desteklenmeyen dosya türü.": "unsupported",
}

_CORRUPT_REASONS = {
    "pdf": "corrupt_pdf",
    "image": "corrupt_image",
}


def _failure_reason(path: Path, error: str | None) -> str:
    reason = _ERROR_REASONS.get(error or "")

    if reason is not None:
        return reason

    if error and "bozuk" in error:
        return _CORRUPT_REASONS.get(
            SUPPORTED_EXTENSIONS.get(path.suffix.lower(), ""),
            "corrupt_office",
        )

    return "unknown"


def _precheck_failure(path: Path) -> str | None:
    if not path.is_file():
        return "not_found"

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return "unsupported"

    try:
        if path.stat().st_size == 0:
            return "empty"

        with path.open("rb") as handle:
            handle.read(1)

    except PermissionError:
        return "no_access"

    except OSError:
        return "unreadable"

    return None


def _find_existing(path: Path) -> tuple[str | None, bool]:
    try:
        sha256 = calculate_sha256(path)

        with _scope() as session:
            existing = SQLAlchemyDocumentRepository(
                session
            ).get_by_sha256(sha256)

            if existing is None:
                return None, False

            return existing.display_name, existing.status == "trashed"

    except Exception:
        return None, False


def import_documents(
    source_paths: list[str],
) -> list[ImportOutcome]:
    service = ImportDocumentService(AppPaths())
    outcomes: list[ImportOutcome] = []

    for raw_path in source_paths:
        path = Path(raw_path)

        reason = _precheck_failure(path)

        if reason is not None:
            outcomes.append(ImportOutcome(raw_path, "failed", reason))
            continue

        try:
            result = service.import_document(path)

        except Exception:
            outcomes.append(ImportOutcome(raw_path, "failed", "save_failed"))
            continue

        if result.imported:
            outcomes.append(ImportOutcome(raw_path, "imported"))

        elif result.duplicate_document is not None:
            name, trashed = _find_existing(path)

            outcomes.append(
                ImportOutcome(
                    raw_path,
                    "duplicate",
                    existing_name=name,
                    existing_trashed=trashed,
                )
            )

        else:
            outcomes.append(
                ImportOutcome(
                    raw_path,
                    "failed",
                    _failure_reason(path, result.error),
                )
            )

    return outcomes
