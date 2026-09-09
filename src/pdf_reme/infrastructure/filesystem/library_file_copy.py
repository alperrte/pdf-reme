import shutil
from pathlib import Path
from uuid import uuid4

from pdf_reme.infrastructure.filesystem.library_path_resolver import (
    resolve_import_directory,
)
from pdf_reme.shared.paths.app_paths import AppPaths


def copy_file_to_library(
    source_path: str | Path,
    document_type: str,
    paths: AppPaths,
) -> Path:
    source = Path(source_path)

    if not source.is_file():
        raise FileNotFoundError(
            f"Kaynak dosya bulunamadı: {source}"
        )

    target_directory = resolve_import_directory(
        document_type,
        paths,
    )

    target_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_path = target_directory / source.name

    # Aynı isimde başka bir dosya varsa üzerine yazma.
    if target_path.exists():
        unique_suffix = uuid4().hex[:8]

        target_path = target_directory / (
            f"{source.stem}_{unique_suffix}{source.suffix}"
        )

    temp_path = target_path.with_suffix(
        target_path.suffix + ".part"
    )

    try:
        shutil.copy2(source, temp_path)
        temp_path.replace(target_path)

    except Exception:
        if temp_path.exists():
            temp_path.unlink()

        raise

    return target_path