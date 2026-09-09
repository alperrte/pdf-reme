from pathlib import Path

from pdf_reme.shared.paths.app_paths import AppPaths


def resolve_import_directory(
    document_type: str,
    paths: AppPaths,
) -> Path:
    mapping = {
        "pdf": paths.imported_pdf_dir,
        "word": paths.imported_word_dir,
        "powerpoint": paths.imported_powerpoint_dir,
        "image": paths.imported_images_dir,
    }

    try:
        return mapping[document_type]
    except KeyError as exc:
        raise ValueError(
            f"Desteklenmeyen belge türü: {document_type}"
        ) from exc
    