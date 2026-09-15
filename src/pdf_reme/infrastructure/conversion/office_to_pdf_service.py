import shutil
import subprocess
import tempfile
from pathlib import Path
from pypdf import PdfReader

class OfficeToPdfService:
    SUPPORTED_EXTENSIONS = {
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
    }

    def __init__(
        self,
        runtime_path: str | Path | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.runtime_path = (
            Path(runtime_path)
            if runtime_path is not None
            else None
        )

        self.timeout_seconds = timeout_seconds

    def convert(
        self,
        input_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        source_path = Path(input_path)
        target_path = Path(output_path)

        self._validate_source(source_path)
        self._validate_output_path(
            source_path,
            target_path,
        )

        soffice_path = self._resolve_soffice()

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.TemporaryDirectory(
            prefix="pdf_reme_office_"
        ) as temp_dir:
            temp_path = Path(temp_dir)

            profile_path = (
                temp_path / "profile"
            )

            profile_path.mkdir(
                parents=True,
                exist_ok=True,
            )

            # Kaynağı LibreOffice için sade bir
            # geçici çalışma yoluna alıyoruz.
            staged_source = (
                temp_path
                / f"source{source_path.suffix.lower()}"
            )

            shutil.copy2(
                source_path,
                staged_source,
            )

            try:
                result = subprocess.run(
                    [
                        str(soffice_path),
                        "--headless",
                        "--nologo",
                        "--nodefault",
                        "--nofirststartwizard",
                        (
                            "-env:UserInstallation="
                            f"{profile_path.resolve().as_uri()}"
                        ),
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(temp_path),
                        str(staged_source),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )

            except subprocess.TimeoutExpired as exc:
                raise TimeoutError(
                    "Office → PDF dönüşümü "
                    "zaman aşımına uğradı."
                ) from exc

            if result.returncode != 0:
                raise RuntimeError(
                    "LibreOffice dönüşümü başarısız oldu. "
                    f"Çıkış kodu: {result.returncode}. "
                    f"Hata: {result.stderr.strip()}"
                )

            generated_pdf = (
                temp_path / "source.pdf"
            )

            if not generated_pdf.exists():
                raise RuntimeError(
                    "LibreOffice dönüşüm sonrasında "
                    "PDF dosyası oluşturmadı. "
                    f"stdout: {result.stdout.strip()} "
                    f"stderr: {result.stderr.strip()}"
                )

            if generated_pdf.stat().st_size == 0:
                raise RuntimeError(
                    "LibreOffice boş bir PDF oluşturdu."
                )

            try:
                reader = PdfReader(
                    str(generated_pdf)
                )

                if len(reader.pages) == 0:
                    raise RuntimeError(
                        "Oluşturulan PDF içerisinde "
                        "sayfa bulunamadı."
                    )

            except RuntimeError:
                raise

            except Exception as exc:
                raise RuntimeError(
                    "LibreOffice geçerli bir PDF "
                    "oluşturmadı."
                ) from exc

            try:
                shutil.move(
                    str(generated_pdf),
                    str(target_path),
                )

            except Exception:
                if target_path.exists():
                    target_path.unlink()

                raise

        return target_path

    def _resolve_soffice(self) -> Path:
        if self.runtime_path is not None:
            candidate = self.runtime_path

            if candidate.is_dir():
                if self._is_windows():
                    candidates = [
                        candidate / "program" / "soffice.com",
                        candidate / "program" / "soffice.exe",
                    ]
                else:
                    candidates = [
                        candidate / "program" / "soffice",
                    ]

                for executable in candidates:
                    if (
                        executable.exists()
                        and executable.is_file()
                    ):
                        return executable

                raise FileNotFoundError(
                    "Bundled LibreOffice Runtime bulunamadı: "
                    f"{candidate}"
                )

            if (
                candidate.exists()
                and candidate.is_file()
            ):
                return candidate

            raise FileNotFoundError(
                "Bundled LibreOffice Runtime bulunamadı: "
                f"{candidate}"
            )

        if self._is_windows():
            common_paths = [
                Path(
                    r"C:\Program Files\LibreOffice\program\soffice.com"
                ),
                Path(
                    r"C:\Program Files\LibreOffice\program\soffice.exe"
                ),
                Path(
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.com"
                ),
                Path(
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
                ),
            ]

            for candidate in common_paths:
                if (
                    candidate.exists()
                    and candidate.is_file()
                ):
                    return candidate

        for executable_name in (
            "soffice.com",
            "soffice",
            "libreoffice",
        ):
            executable = shutil.which(
                executable_name
            )

            if executable:
                return Path(executable)

        raise FileNotFoundError(
            "LibreOffice Runtime bulunamadı. "
            "Bundled runtime yolu yapılandırılmalıdır."
        )

    def _validate_source(
        self,
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                "Office dosyası bulunamadı: "
                f"{source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                "Office kaynağı bir dosya olmalıdır."
            )

        if (
            source_path.suffix.lower()
            not in self.SUPPORTED_EXTENSIONS
        ):
            raise ValueError(
                "Yalnızca DOC, DOCX, PPT, PPTX, "
                "XLS ve XLSX dosyaları "
                "PDF'e dönüştürülebilir."
            )

    def _validate_output_path(
        self,
        source_path: Path,
        output_path: Path,
    ) -> None:
        if (
            output_path.suffix.lower()
            != ".pdf"
        ):
            raise ValueError(
                "Çıktı dosyası PDF formatında olmalıdır."
            )

        if (
            source_path.resolve()
            == output_path.resolve()
        ):
            raise ValueError(
                "Çıktı dosyası kaynak dosya "
                "ile aynı olamaz."
            )

    @staticmethod
    def _is_windows() -> bool:
        import os

        return os.name == "nt"