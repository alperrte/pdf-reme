from pathlib import Path

from pypdf import PdfReader, PdfWriter


class PdfPageEditService:
    def reorder_pages(
        self,
        input_path: str | Path,
        page_order: list[int],
        output_path: str | Path,
    ) -> Path:
        source_path = Path(input_path)
        target_path = Path(output_path)

        self._validate_source(source_path)
        self._validate_output_path(
            source_path,
            target_path,
        )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                f"Şifreli PDF düzenlenemez: {source_path.name}"
            )

        total_pages = len(reader.pages)

        if not page_order:
            raise ValueError(
                "Sayfa sıralaması boş olamaz."
            )

        expected_pages = list(
            range(1, total_pages + 1)
        )

        if sorted(page_order) != expected_pages:
            raise ValueError(
                "Yeni sayfa sıralaması belgedeki tüm sayfaları "
                "tam olarak bir kez içermelidir."
            )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        writer = PdfWriter()

        try:
            for page_number in page_order:
                writer.add_page(
                    reader.pages[page_number - 1]
                )

            with target_path.open("wb") as output_file:
                writer.write(output_file)

        except Exception:
            if target_path.exists():
                target_path.unlink()

            raise

        return target_path

    def _validate_source(
        self,
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                f"Düzenlenecek PDF bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"PDF kaynağı bir dosya olmalıdır: {source_path}"
            )

        if source_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Yalnızca PDF dosyaları düzenlenebilir: {source_path}"
            )

    def _validate_output_path(
        self,
        source_path: Path,
        output_path: Path,
    ) -> None:
        if source_path.resolve() == output_path.resolve():
            raise ValueError(
                "Çıktı dosyası kaynak PDF ile aynı olamaz."
            )

    def swap_pages(
        self,
        input_path: str | Path,
        first_page: int,
        second_page: int,
        output_path: str | Path,
    ) -> Path:
        source_path = Path(input_path)
        target_path = Path(output_path)

        self._validate_source(source_path)
        self._validate_output_path(
            source_path,
            target_path,
        )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                f"Şifreli PDF düzenlenemez: {source_path.name}"
            )

        total_pages = len(reader.pages)

        for page_number in (
            first_page,
            second_page,
        ):
            if (
                page_number < 1
                or page_number > total_pages
            ):
                raise ValueError(
                    f"Geçersiz sayfa numarası: {page_number}"
                )

        if first_page == second_page:
            raise ValueError(
                "Yer değiştirilecek sayfalar farklı olmalıdır."
            )

        page_order = list(
            range(1, total_pages + 1)
        )

        first_index = first_page - 1
        second_index = second_page - 1

        page_order[first_index], page_order[second_index] = (
            page_order[second_index],
            page_order[first_index],
        )

        return self.reorder_pages(
            input_path=source_path,
            page_order=page_order,
            output_path=target_path,
        )

    def delete_pages(
        self,
        input_path: str | Path,
        page_numbers: list[int],
        output_path: str | Path,
    ) -> Path:
        source_path = Path(input_path)
        target_path = Path(output_path)

        self._validate_source(source_path)
        self._validate_output_path(
            source_path,
            target_path,
        )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                f"Şifreli PDF düzenlenemez: {source_path.name}"
            )

        total_pages = len(reader.pages)

        if not page_numbers:
            raise ValueError(
                "Silinecek en az bir sayfa seçilmelidir."
            )

        unique_pages = sorted(set(page_numbers))

        for page_number in unique_pages:
            if (
                page_number < 1
                or page_number > total_pages
            ):
                raise ValueError(
                    f"Geçersiz sayfa numarası: {page_number}"
                )

        if len(unique_pages) == total_pages:
            raise ValueError(
                "PDF içerisindeki tüm sayfalar silinemez."
            )

        pages_to_delete = set(unique_pages)

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        writer = PdfWriter()

        try:
            for page_number in range(
                1,
                total_pages + 1,
            ):
                if page_number not in pages_to_delete:
                    writer.add_page(
                        reader.pages[page_number - 1]
                    )

            with target_path.open("wb") as output_file:
                writer.write(output_file)

        except Exception:
            if target_path.exists():
                target_path.unlink()

            raise

        return target_path