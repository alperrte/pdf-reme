from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from pdf_reme.domain.repositories.document_repository import DocumentRepository
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.pdf.pdf_page_edit_service import (
    PdfPageEditService,
)
from pdf_reme.shared.paths.app_paths import AppPaths


class EditPdfPagesUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        page_edit_service: PdfPageEditService,
        paths: AppPaths,
    ) -> None:
        self.repository = repository
        self.page_edit_service = page_edit_service
        self.paths = paths

    def reorder_pages(
        self,
        input_path: str | Path,
        page_order: list[int],
        display_name: str,
    ) -> Document:
        clean_name = self._validate_file_name(
            display_name
        )

        output_path = self._create_output_path(
            clean_name
        )

        try:
            self.page_edit_service.reorder_pages(
                input_path=input_path,
                page_order=page_order,
                output_path=output_path,
            )

            return self._save_generated_document(
                output_path=output_path,
                generation_type="page_reorder",
            )

        except Exception:
            self._cleanup_output(
                output_path
            )
            raise

    def swap_pages(
        self,
        input_path: str | Path,
        first_page: int,
        second_page: int,
        display_name: str,
    ) -> Document:
        clean_name = self._validate_file_name(
            display_name
        )

        output_path = self._create_output_path(
            clean_name
        )

        try:
            self.page_edit_service.swap_pages(
                input_path=input_path,
                first_page=first_page,
                second_page=second_page,
                output_path=output_path,
            )

            return self._save_generated_document(
                output_path=output_path,
                generation_type="page_swap",
            )

        except Exception:
            self._cleanup_output(
                output_path
            )
            raise

    def delete_pages(
        self,
        input_path: str | Path,
        page_numbers: list[int],
        display_name: str,
    ) -> Document:
        clean_name = self._validate_file_name(
            display_name
        )

        output_path = self._create_output_path(
            clean_name
        )

        try:
            self.page_edit_service.delete_pages(
                input_path=input_path,
                page_numbers=page_numbers,
                output_path=output_path,
            )

            return self._save_generated_document(
                output_path=output_path,
                generation_type="page_delete",
            )

        except Exception:
            self._cleanup_output(
                output_path
            )
            raise

    def _save_generated_document(
        self,
        output_path: Path,
        generation_type: str,
    ) -> Document:
        file_hash = sha256(
            output_path.read_bytes()
        ).hexdigest()

        reader = PdfReader(
            str(output_path)
        )

        document = Document(
            display_name=output_path.name,
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

        return self.repository.add(
            document
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

    def _create_output_path(
        self,
        file_name: str,
    ) -> Path:
        self.paths.generated_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

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

    def _cleanup_output(
        self,
        output_path: Path,
    ) -> None:
        if output_path.exists():
            output_path.unlink()

    def rotate_pages(
    self,
    input_path: str | Path,
    page_numbers: list[int],
    degrees: int,
    display_name: str,
    ) -> Document:
        clean_name = self._validate_file_name(display_name)
        output_path = self._create_output_path(clean_name)

        try:
            self.page_edit_service.rotate_pages(
                input_path=input_path,
                page_numbers=page_numbers,
                degrees=degrees,
                output_path=output_path,
            )

            return self._save_generated_document(
                output_path,
                "page_rotate",
            )

        except Exception:
            self._cleanup_output(output_path)
            raise


    def duplicate_pages(
        self,
        input_path: str | Path,
        page_numbers: list[int],
        display_name: str,
    ) -> Document:
        clean_name = self._validate_file_name(display_name)
        output_path = self._create_output_path(clean_name)

        try:
            self.page_edit_service.duplicate_pages(
                input_path=input_path,
                page_numbers=page_numbers,
                output_path=output_path,
            )

            return self._save_generated_document(
                output_path,
                "page_duplicate",
            )

        except Exception:
            self._cleanup_output(output_path)
            raise


    def insert_pages(
        self,
        input_path: str | Path,
        insert_pdf_path: str | Path,
        source_page_numbers: list[int],
        after_page: int,
        display_name: str,
    ) -> Document:
        clean_name = self._validate_file_name(display_name)
        output_path = self._create_output_path(clean_name)

        try:
            self.page_edit_service.insert_pages(
                input_path=input_path,
                insert_pdf_path=insert_pdf_path,
                source_page_numbers=source_page_numbers,
                after_page=after_page,
                output_path=output_path,
            )

            return self._save_generated_document(
                output_path,
                "page_insert",
            )

        except Exception:
            self._cleanup_output(output_path)
            raise


    def insert_blank_page(
        self,
        input_path: str | Path,
        after_page: int,
        display_name: str,
    ) -> Document:
        clean_name = self._validate_file_name(display_name)
        output_path = self._create_output_path(clean_name)

        try:
            self.page_edit_service.insert_blank_page(
                input_path=input_path,
                after_page=after_page,
                output_path=output_path,
            )

            return self._save_generated_document(
                output_path,
                "page_blank_insert",
            )

        except Exception:
            self._cleanup_output(output_path)
            raise