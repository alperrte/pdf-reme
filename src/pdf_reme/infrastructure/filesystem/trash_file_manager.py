import shutil
from pathlib import Path
from uuid import uuid4

from pdf_reme.shared.paths.app_paths import AppPaths


class TrashFileManager:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def move_to_trash(self, file_path: str | Path) -> Path:
        source_path = Path(file_path)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Çöp kutusuna taşınacak dosya bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"Çöp kutusuna yalnızca dosyalar taşınabilir: {source_path}"
            )

        self.paths.trash_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path = self.paths.trash_dir / source_path.name

        if target_path.exists():
            target_path = self._create_unique_trash_target(
                source_path.name
            )

        shutil.move(
            str(source_path),
            str(target_path),
        )

        return target_path

    def restore_from_trash(
        self,
        trash_path: str | Path,
        restore_path: str | Path,
    ) -> Path:
        source_path = Path(trash_path)
        target_path = Path(restore_path)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Geri yüklenecek dosya bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"Yalnızca dosyalar geri yüklenebilir: {source_path}"
            )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if target_path.exists():
            target_path = self._create_unique_restore_target(
                target_path
            )

        shutil.move(
            str(source_path),
            str(target_path),
        )

        return target_path

    def permanently_delete(
        self,
        trash_path: str | Path,
    ) -> bool:
        file_path = Path(trash_path)

        trash_root = self.paths.trash_dir.resolve()
        resolved_path = file_path.resolve()

        if not resolved_path.is_relative_to(trash_root):
            raise ValueError(
                "Yalnızca PDF-REME çöp kutusundaki dosyalar "
                "kalıcı olarak silinebilir."
            )

        if not file_path.exists():
            return False

        if not file_path.is_file():
            raise ValueError(
                f"Yalnızca dosyalar kalıcı olarak silinebilir: {file_path}"
            )

        file_path.unlink()

        return True

    def _create_unique_trash_target(
        self,
        file_name: str,
    ) -> Path:
        file_path = Path(file_name)

        unique_name = (
            f"{file_path.stem}_"
            f"{uuid4().hex[:8]}"
            f"{file_path.suffix}"
        )

        return self.paths.trash_dir / unique_name

    def _create_unique_restore_target(
        self,
        target_path: Path,
    ) -> Path:
        unique_name = (
            f"{target_path.stem}_"
            f"{uuid4().hex[:8]}"
            f"{target_path.suffix}"
        )

        return target_path.parent / unique_name