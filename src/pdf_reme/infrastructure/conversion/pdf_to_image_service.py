from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtPdf import QPdfDocument
from pypdf import PdfReader


class PdfToImageService:
    def convert_to_jpg(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        base_name: str,
        page_numbers: list[int] | None = None,
        dpi: int = 150,
        quality: int = 90,
    ) -> list[Path]:
        source_path = Path(input_path)
        target_dir = Path(output_dir)

        self._validate_source(source_path)

        if dpi < 72 or dpi > 600:
            raise ValueError(
                "DPI değeri 72 ile 600 arasında olmalıdır."
            )

        if quality < 1 or quality > 100:
            raise ValueError(
                "JPG kalite değeri 1 ile 100 arasında olmalıdır."
            )

        clean_base_name = base_name.strip()

        if not clean_base_name:
            raise ValueError(
                "Çıktı için temel dosya adı gereklidir."
            )

        reader = PdfReader(str(source_path))

        if reader.is_encrypted:
            raise ValueError(
                "Şifreli PDF doğrudan JPG formatına dönüştürülemez."
            )

        total_pages = len(reader.pages)

        selected_pages = self._resolve_pages(
            page_numbers=page_numbers,
            total_pages=total_pages,
        )

        target_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        document = QPdfDocument()

        error = document.load(
            str(source_path)
        )

        if error != QPdfDocument.Error.None_:
            document.close()
            raise ValueError(
                f"PDF görüntülenemedi: {source_path.name}"
            )

        output_paths: list[Path] = []

        try:
            for page_number in selected_pages:
                page_index = page_number - 1

                point_size = document.pagePointSize(
                    page_index
                )

                scale = dpi / 72.0

                image_size = QSize(
                    max(
                        1,
                        round(
                            point_size.width()
                            * scale
                        ),
                    ),
                    max(
                        1,
                        round(
                            point_size.height()
                            * scale
                        ),
                    ),
                )

                image = document.render(
                    page_index,
                    image_size,
                )

                if image.isNull():
                    raise RuntimeError(
                        "PDF sayfası görüntüye "
                        f"dönüştürülemedi: {page_number}"
                    )

                output_path = (
                    target_dir
                    / (
                        f"{clean_base_name}"
                        f"_page_{page_number}.jpg"
                    )
                )

                self._save_image(
                    image=image,
                    output_path=output_path,
                    quality=quality,
                )

                output_paths.append(
                    output_path
                )

        except Exception:
            for output_path in output_paths:
                if output_path.exists():
                    output_path.unlink()

            raise

        finally:
            document.close()

        return output_paths

    def _resolve_pages(
        self,
        page_numbers: list[int] | None,
        total_pages: int,
    ) -> list[int]:
        if total_pages <= 0:
            raise ValueError(
                "PDF içerisinde sayfa bulunamadı."
            )

        if page_numbers is None:
            return list(
                range(1, total_pages + 1)
            )

        if not page_numbers:
            raise ValueError(
                "En az bir PDF sayfası seçilmelidir."
            )

        resolved_pages: list[int] = []
        seen: set[int] = set()

        for page_number in page_numbers:
            if (
                page_number < 1
                or page_number > total_pages
            ):
                raise ValueError(
                    "Geçersiz sayfa numarası: "
                    f"{page_number}"
                )

            if page_number not in seen:
                seen.add(page_number)
                resolved_pages.append(
                    page_number
                )

        return resolved_pages

    def _validate_source(
        self,
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                f"PDF bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                "PDF kaynağı bir dosya olmalıdır."
            )

        if (
            source_path.suffix.lower()
            != ".pdf"
        ):
            raise ValueError(
                "Yalnızca PDF dosyaları "
                "JPG formatına dönüştürülebilir."
            )

    def _save_image(
        self,
        image,
        output_path: Path,
        quality: int,
    ) -> None:
        success = image.save(
            str(output_path),
            "JPG",
            quality,
        )

        if not success:
            raise RuntimeError(
                "JPG dosyası kaydedilemedi: "
                f"{output_path.name}"
            )