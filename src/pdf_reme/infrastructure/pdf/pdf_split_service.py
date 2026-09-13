from pathlib import Path

from pypdf import PdfReader, PdfWriter


class PdfSplitService:
    def extract_pages(
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

        if not page_numbers:
            raise ValueError(
                "En az bir sayfa seçilmelidir."
            )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                f"Şifreli PDF bölünemez: {source_path.name}"
            )

        total_pages = len(reader.pages)

        for page_number in page_numbers:
            if page_number < 1 or page_number > total_pages:
                raise ValueError(
                    f"Geçersiz sayfa numarası: {page_number}"
                )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        writer = PdfWriter()

        try:
            for page_number in page_numbers:
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

    def split_into_parts(
        self,
        input_path: str | Path,
        part_count: int,
        output_dir: str | Path,
        base_name: str = "split",
    ) -> list[Path]:
        source_path = Path(input_path)
        target_dir = Path(output_dir)

        self._validate_source(source_path)

        if part_count < 2:
            raise ValueError(
                "PDF en az iki parçaya bölünmelidir."
            )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                f"Şifreli PDF bölünemez: {source_path.name}"
            )

        total_pages = len(reader.pages)

        if part_count > total_pages:
            raise ValueError(
                "Parça sayısı toplam sayfa sayısından büyük olamaz."
            )

        target_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        base_size, remainder = divmod(
            total_pages,
            part_count,
        )

        output_paths: list[Path] = []
        current_page = 0

        try:
            for part_index in range(part_count):
                part_size = base_size

                if part_index < remainder:
                    part_size += 1

                writer = PdfWriter()

                for _ in range(part_size):
                    writer.add_page(
                        reader.pages[current_page]
                    )
                    current_page += 1

                output_path = (
                    target_dir
                    / f"{base_name}_part_{part_index + 1}.pdf"
                )

                self._validate_output_path(
                    source_path,
                    output_path,
                )

                with output_path.open("wb") as output_file:
                    writer.write(output_file)

                output_paths.append(output_path)

        except Exception:
            for output_path in output_paths:
                if output_path.exists():
                    output_path.unlink()

            raise

        return output_paths

    def split_by_groups(
        self,
        input_path: str | Path,
        page_groups: list[list[int]],
        output_dir: str | Path,
        base_name: str = "split",
    ) -> list[Path]:
        source_path = Path(input_path)
        target_dir = Path(output_dir)

        self._validate_source(source_path)

        if not page_groups:
            raise ValueError(
                "En az bir sayfa grubu gereklidir."
            )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                f"Şifreli PDF bölünemez: {source_path.name}"
            )

        total_pages = len(reader.pages)

        target_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_paths: list[Path] = []

        try:
            for group_index, page_numbers in enumerate(
                page_groups,
                start=1,
            ):
                if not page_numbers:
                    raise ValueError(
                        "Sayfa grupları boş olamaz."
                    )

                writer = PdfWriter()

                for page_number in page_numbers:
                    if (
                        page_number < 1
                        or page_number > total_pages
                    ):
                        raise ValueError(
                            f"Geçersiz sayfa numarası: "
                            f"{page_number}"
                        )

                    writer.add_page(
                        reader.pages[page_number - 1]
                    )

                output_path = (
                    target_dir
                    / f"{base_name}_group_{group_index}.pdf"
                )

                self._validate_output_path(
                    source_path,
                    output_path,
                )

                with output_path.open("wb") as output_file:
                    writer.write(output_file)

                output_paths.append(output_path)

        except Exception:
            for output_path in output_paths:
                if output_path.exists():
                    output_path.unlink()

            raise

        return output_paths

    def _validate_source(
        self,
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                f"Bölünecek PDF bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"PDF kaynağı bir dosya olmalıdır: {source_path}"
            )

        if source_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Yalnızca PDF dosyaları bölünebilir: {source_path}"
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