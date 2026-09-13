from pathlib import Path

from pypdf import PdfReader, PdfWriter


class PdfMergeService:
    def merge(
        self,
        input_paths: list[str | Path],
        output_path: str | Path,
    ) -> Path:
        if len(input_paths) < 2:
            raise ValueError(
                "PDF birleştirme işlemi için en az iki dosya gereklidir."
            )

        source_paths = [
            Path(path)
            for path in input_paths
        ]

        target_path = Path(output_path)

        for source_path in source_paths:
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Birleştirilecek PDF bulunamadı: {source_path}"
                )

            if not source_path.is_file():
                raise ValueError(
                    f"Birleştirme kaynağı bir dosya olmalıdır: {source_path}"
                )

            if source_path.suffix.lower() != ".pdf":
                raise ValueError(
                    f"Yalnızca PDF dosyaları birleştirilebilir: {source_path}"
                )

        resolved_target = target_path.resolve()

        for source_path in source_paths:
            if source_path.resolve() == resolved_target:
                raise ValueError(
                    "Çıktı dosyası kaynak PDF dosyalarından biri olamaz."
                )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        writer = PdfWriter()

        try:
            for source_path in source_paths:
                reader = PdfReader(str(source_path))

                if reader.is_encrypted:
                    raise ValueError(
                        f"Şifreli PDF birleştirilemez: {source_path.name}"
                    )

                for page in reader.pages:
                    writer.add_page(page)

            with target_path.open("wb") as output_file:
                writer.write(output_file)

        except Exception:
            if target_path.exists():
                target_path.unlink()

            raise

        return target_path