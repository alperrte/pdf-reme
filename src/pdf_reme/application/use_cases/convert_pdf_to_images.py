from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pdf_reme.domain.repositories.document_repository import (
    DocumentRepository,
)
from pdf_reme.infrastructure.conversion.pdf_to_image_service import (
    PdfToImageService,
)
from pdf_reme.infrastructure.database.models.document import (
    Document,
)
from pdf_reme.shared.paths.app_paths import AppPaths


class ConvertPdfToImagesUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        conversion_service: PdfToImageService,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.conversion_service = conversion_service
        self.paths = paths

    def execute(
        self,
        input_path: str | Path,
        base_name: str,
        page_numbers: list[int] | None = None,
        dpi: int = 150,
        quality: int = 90,
    ) -> list[Document]:
        clean_base_name = self._validate_base_name(
            base_name
        )

        unique_base_name = (
            self._create_unique_base_name(
                clean_base_name
            )
        )

        created_paths: list[Path] = []

        try:
            created_paths = (
                self.conversion_service.convert_to_jpg(
                    input_path=input_path,
                    output_dir=self.paths.generated_dir,
                    base_name=unique_base_name,
                    page_numbers=page_numbers,
                    dpi=dpi,
                    quality=quality,
                )
            )

            documents: list[Document] = []

            for output_path in created_paths:
                document = Document(
                    display_name=output_path.name,
                    stored_path=str(output_path),
                    original_path=None,
                    document_type="image",
                    library_section="generated",
                    generation_type="pdf_to_jpg",
                    sha256=sha256(
                        output_path.read_bytes()
                    ).hexdigest(),
                    file_size=(
                        output_path.stat().st_size
                    ),
                    page_count=None,
                    is_favorite=False,
                    status="active",
                )

                documents.append(
                    self.repository.add(
                        document
                    )
                )

            return documents

        except Exception:
            for output_path in created_paths:
                if output_path.exists():
                    output_path.unlink()

            raise

    def _validate_base_name(
        self,
        base_name: str,
    ) -> str:
        clean_name = base_name.strip()

        if not clean_name:
            raise ValueError(
                "Çıktı için temel dosya adı gereklidir."
            )

        if (
            "/" in clean_name
            or "\\" in clean_name
            or Path(clean_name).name
            != clean_name
        ):
            raise ValueError(
                "Dosya adı klasör yolu içeremez."
            )

        if clean_name.lower().endswith(
            ".jpg"
        ):
            clean_name = Path(
                clean_name
            ).stem

        return clean_name

    def _create_unique_base_name(
        self,
        base_name: str,
    ) -> str:
        self.paths.generated_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        existing_files = list(
            self.paths.generated_dir.glob(
                f"{base_name}_page_*.jpg"
            )
        )

        if not existing_files:
            return base_name

        return (
            f"{base_name}_"
            f"{uuid4().hex[:8]}"
        )