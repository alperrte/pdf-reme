import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from pdf_reme.infrastructure.pdf.pdf_compression_engine import (
    PdfCompressionEngine,
)


@dataclass(frozen=True)
class PdfCompressionResult:
    output_path: Path
    level: str
    original_size: int
    compressed_size: int
    saved_bytes: int
    savings_percent: float
    used_original_fallback: bool


class PdfCompressionService:
    LEVELS = {
        "light",
        "balanced",
        "strong",
    }

    def __init__(
        self,
        engine: PdfCompressionEngine | None = None,
    ) -> None:
        self.engine = (
            engine
            or PdfCompressionEngine()
        )

    def compress(
        self,
        input_path: str | Path,
        output_path: str | Path,
        level: str = "balanced",
    ) -> PdfCompressionResult:
        source_path = Path(
            input_path
        )

        target_path = Path(
            output_path
        )

        self._validate(
            source_path,
            target_path,
            level,
        )

        source_reader = PdfReader(
            str(source_path)
        )

        if source_reader.is_encrypted:
            raise ValueError(
                "Şifreli PDF doğrudan "
                "sıkıştırılamaz."
            )

        source_page_count = len(
            source_reader.pages
        )

        original_size = (
            source_path.stat().st_size
        )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        used_original_fallback = False

        with tempfile.TemporaryDirectory(
            prefix="pdf_reme_compress_"
        ) as temp_dir:
            temp_output = (
                Path(temp_dir)
                / "compressed.pdf"
            )

            try:
                self.engine.compress(
                    source_path=source_path,
                    output_path=temp_output,
                    level=level,
                )

                if (
                    not temp_output.exists()
                    or temp_output.stat().st_size
                    == 0
                ):
                    raise RuntimeError(
                        "PDF sıkıştırma işlemi "
                        "geçerli bir çıktı oluşturmadı."
                    )

                compressed_reader = PdfReader(
                    str(temp_output)
                )

                if (
                    len(compressed_reader.pages)
                    != source_page_count
                ):
                    raise RuntimeError(
                        "Sıkıştırma sonrasında "
                        "PDF sayfa sayısı değişti."
                    )

                if (
                    temp_output.stat().st_size
                    >= original_size
                ):
                    shutil.copy2(
                        source_path,
                        target_path,
                    )

                    used_original_fallback = True

                else:
                    shutil.move(
                        str(temp_output),
                        str(target_path),
                    )

            except Exception:
                if target_path.exists():
                    target_path.unlink()

                raise

        compressed_size = (
            target_path.stat().st_size
        )

        saved_bytes = max(
            0,
            original_size
            - compressed_size,
        )

        savings_percent = (
            (
                saved_bytes
                / original_size
            )
            * 100
            if original_size
            else 0.0
        )

        return PdfCompressionResult(
            output_path=target_path,
            level=level,
            original_size=original_size,
            compressed_size=compressed_size,
            saved_bytes=saved_bytes,
            savings_percent=round(
                savings_percent,
                2,
            ),
            used_original_fallback=(
                used_original_fallback
            ),
        )

    def _validate(
        self,
        source_path: Path,
        output_path: Path,
        level: str,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                "PDF bulunamadı: "
                f"{source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                "Kaynak bir dosya olmalıdır."
            )

        if (
            source_path.suffix.lower()
            != ".pdf"
        ):
            raise ValueError(
                "Yalnızca PDF dosyaları "
                "sıkıştırılabilir."
            )

        if (
            output_path.suffix.lower()
            != ".pdf"
        ):
            raise ValueError(
                "Çıktı dosyası PDF olmalıdır."
            )

        if (
            source_path.resolve()
            == output_path.resolve()
        ):
            raise ValueError(
                "Kaynak PDF'nin üzerine "
                "yazılamaz."
            )

        if level not in self.LEVELS:
            raise ValueError(
                "Sıkıştırma seviyesi "
                "light, balanced veya strong "
                "olmalıdır."
            )