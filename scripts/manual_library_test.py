import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from pdf_reme.application.services.library_service import LibraryService
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.database.session import session_scope


def main() -> None:
    with session_scope() as session:
        repository = SQLAlchemyDocumentRepository(session)
        service = LibraryService(repository)

        uploaded = service.get_uploaded_documents()
        generated = service.get_generated_documents()
        favorites = service.get_favorites()
        recent = service.get_recent_documents()

        print("=== PDF-REME KÜTÜPHANE TESTİ ===")
        print(f"Yüklenenler: {len(uploaded)}")
        print(f"Oluşturulanlar: {len(generated)}")
        print(f"Favoriler: {len(favorites)}")
        print(f"Son kullanılanlar: {len(recent)}")

        if not uploaded:
            print("\nTest edilecek yüklenmiş belge bulunamadı.")
            return

        document = uploaded[0]

        print("\nTest belgesi:")
        print(f"Ad: {document.display_name}")
        print(f"Favori durumu: {document.is_favorite}")
        print(f"Son açılma: {document.last_opened_at}")

        service.toggle_favorite(document.id)
        service.mark_as_opened(document.id)

        print("\nGüncelleme sonrası:")
        print(f"Favori durumu: {document.is_favorite}")
        print(f"Son açılma: {document.last_opened_at}")

        favorites = service.get_favorites()
        recent = service.get_recent_documents()

        print("\nGüncel kütüphane:")
        print(f"Favoriler: {[item.display_name for item in favorites]}")
        print(f"Son kullanılanlar: {[item.display_name for item in recent]}")


if __name__ == "__main__":
    main()