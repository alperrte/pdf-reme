from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from PIL import Image
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".doc": "word",
    ".docx": "word",
    ".ppt": "powerpoint",
    ".pptx": "powerpoint",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
}


@dataclass(frozen=True)
class FileValidationResult:
    is_valid: bool
    document_type: str | None
    extension: str
    error: str | None = None


def detect_document_type(file_path: str | Path) -> str | None:
    path = Path(file_path)
    return SUPPORTED_EXTENSIONS.get(path.suffix.lower())


def validate_file(file_path: str | Path) -> FileValidationResult:
    path = Path(file_path)

    if not path.is_file():
        return FileValidationResult(
            is_valid=False,
            document_type=None,
            extension=path.suffix.lower(),
            error="Dosya bulunamadı.",
        )

    extension = path.suffix.lower()
    document_type = detect_document_type(path)

    if document_type is None:
        return FileValidationResult(
            is_valid=False,
            document_type=None,
            extension=extension,
            error="Desteklenmeyen dosya türü.",
        )

    try:
        if document_type == "pdf":
            PdfReader(path)

        elif document_type == "image":
            with Image.open(path) as image:
                image.verify()
        elif extension in {".docx", ".pptx"}:
            _validate_ooxml_file(path, document_type)        

    except Exception:
        return FileValidationResult(
            is_valid=False,
            document_type=document_type,
            extension=extension,
            error="Dosya açılamıyor veya bozuk olabilir.",
        )

    return FileValidationResult(
        is_valid=True,
        document_type=document_type,
        extension=extension,
    )

def _validate_ooxml_file(path: Path, document_type: str) -> None:
    try:
        with ZipFile(path, "r") as archive:
            names = set(archive.namelist())

            if "[Content_Types].xml" not in names:
                raise ValueError("Geçersiz Office paketi.")

            if document_type == "word":
                if "word/document.xml" not in names:
                    raise ValueError("Geçersiz DOCX dosyası.")

            elif document_type == "powerpoint":
                if "ppt/presentation.xml" not in names:
                    raise ValueError("Geçersiz PPTX dosyası.")

    except BadZipFile as exc:
        raise ValueError("Geçersiz Office paketi.") from exc