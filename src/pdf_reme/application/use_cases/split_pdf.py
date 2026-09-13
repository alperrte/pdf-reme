from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from pdf_reme.application.services.page_selection_parser import (
    PageSelectionParser,
)
from pdf_reme.domain.repositories.document_repository import DocumentRepository
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.pdf.pdf_split_service import PdfSplitService
from pdf_reme.shared.paths.app_paths import AppPaths


class SplitPdfUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        split_service: PdfSplitService,
        parser: PageSelectionParser,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.split_service = split_service
        self.parser = parser
        self.paths = paths

    def extract_selected_pages(
        self,
        input_path: str | Path,
        page_expression: str,
        display_name: str,
    ) -> Document:
        source_path = Path(input_path)

        clean_name = self._validate_file_name(
            display_name
        )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                f"Şifreli PDF bölünemez: {source_path.name}"
            )

        selected_pages = self.parser.parse(
            expression=page_expression,
            total_pages=len(reader.pages),
        )

        self.paths.generated_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = self._create_unique_output_path(
            clean_name
        )

        try:
            self.split_service.extract_pages(
                input_path=source_path,
                page_numbers=selected_pages,
                output_path=output_path,
            )

            document = self._create_document(
                output_path=output_path,
                display_name=output_path.name,
                generation_type="split_extract",
            )

            return self.repository.add(
                document
            )

        except Exception:
            if output_path.exists():
                output_path.unlink()

            raise

    def split_into_parts(
        self,
        input_path: str | Path,
        part_count: int,
        base_name: str,
    ) -> list[Document]:
        source_path = Path(input_path)

        clean_base_name = self._validate_base_name(
            base_name
        )

        self.paths.generated_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        unique_base_name = self._create_unique_base_name(
            clean_base_name
        )

        output_paths: list[Path] = []
        saved_documents: list[Document] = []

        try:
            output_paths = self.split_service.split_into_parts(
                input_path=source_path,
                part_count=part_count,
                output_dir=self.paths.generated_dir,
                base_name=unique_base_name,
            )

            for output_path in output_paths:
                document = self._create_document(
                    output_path=output_path,
                    display_name=output_path.name,
                    generation_type="split_parts",
                )

                saved = self.repository.add(
                    document
                )

                saved_documents.append(
                    saved
                )

            return saved_documents

        except Exception:
            for output_path in output_paths:
                if output_path.exists():
                    output_path.unlink()

            for document in saved_documents:
                if document.id is not None:
                    try:
                        self.repository.delete(
                            document.id
                        )
                    except Exception:
                        pass

            raise

    def split_by_groups(
        self,
        input_path: str | Path,
        page_groups: list[list[int]],
        base_name: str,
    ) -> list[Document]:
        source_path = Path(input_path)

        clean_base_name = self._validate_base_name(
            base_name
        )

        self.paths.generated_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        unique_base_name = self._create_unique_base_name(
            clean_base_name
        )

        output_paths: list[Path] = []
        saved_documents: list[Document] = []

        try:
            output_paths = self.split_service.split_by_groups(
                input_path=source_path,
                page_groups=page_groups,
                output_dir=self.paths.generated_dir,
                base_name=unique_base_name,
            )

            for output_path in output_paths:
                document = self._create_document(
                    output_path=output_path,
                    display_name=output_path.name,
                    generation_type="split_groups",
                )

                saved = self.repository.add(
                    document
                )

                saved_documents.append(
                    saved
                )

            return saved_documents

        except Exception:
            for output_path in output_paths:
                if output_path.exists():
                    output_path.unlink()

            for document in saved_documents:
                if document.id is not None:
                    try:
                        self.repository.delete(
                            document.id
                        )
                    except Exception:
                        pass

            raise

    def _create_document(
        self,
        output_path: Path,
        display_name: str,
        generation_type: str,
    ) -> Document:
        file_bytes = output_path.read_bytes()

        file_hash = sha256(
            file_bytes
        ).hexdigest()

        reader = PdfReader(
            str(output_path)
        )

        return Document(
            display_name=display_name,
            stored_path=str(output_path),
            original_path=None,
            document_type="pdf",
            library_section="generated",
            generation_type=generation_type,
            sha256=file_hash,
            file_size=output_path.stat().st_size,
            page_count=len(reader.pages),
            is_favorite=False,
            status="active",
        )

    def _validate_file_name(
        self,
        file_name: str,
    ) -> str:
        clean_name = file_name.strip()

        if not clean_name:
            raise ValueError(
                "Çıktı dosya adı gereklidir."
            )

        if (
            "/" in clean_name
            or "\\" in clean_name
            or Path(clean_name).name != clean_name
        ):
            raise ValueError(
                "Dosya adı klasör yolu içeremez."
            )

        if not clean_name.lower().endswith(".pdf"):
            clean_name += ".pdf"

        return clean_name

    def _validate_base_name(
        self,
        base_name: str,
    ) -> str:
        clean_name = base_name.strip()

        if not clean_name:
            raise ValueError(
                "Çıktı adı gereklidir."
            )

        if (
            "/" in clean_name
            or "\\" in clean_name
            or Path(clean_name).name != clean_name
        ):
            raise ValueError(
                "Çıktı adı klasör yolu içeremez."
            )

        if clean_name.lower().endswith(".pdf"):
            clean_name = clean_name[:-4]

        return clean_name

    def _create_unique_output_path(
        self,
        file_name: str,
    ) -> Path:
        requested_path = (
            self.paths.generated_dir
            / file_name
        )

        if not requested_path.exists():
            return requested_path

        file_path = Path(file_name)

        unique_name = (
            f"{file_path.stem}_"
            f"{uuid4().hex[:8]}"
            f"{file_path.suffix}"
        )

        return (
            self.paths.generated_dir
            / unique_name
        )

    def _create_unique_base_name(
        self,
        base_name: str,
    ) -> str:
        matching_files = list(
            self.paths.generated_dir.glob(
                f"{base_name}_*.pdf"
            )
        )

        if not matching_files:
            return base_name

        return (
            f"{base_name}_"
            f"{uuid4().hex[:8]}"
        )