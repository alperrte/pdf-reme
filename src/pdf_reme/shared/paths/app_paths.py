import os
import sys
from pathlib import Path


APP_NAME = "PDF-REME"


def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        local_app_data = os.getenv("LOCALAPPDATA")

        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA ortam değişkeni bulunamadı.")

        return Path(local_app_data) / APP_NAME

    if sys.platform.startswith("linux"):
        xdg_data_home = os.getenv("XDG_DATA_HOME")

        if xdg_data_home:
            return Path(xdg_data_home) / APP_NAME

        return Path.home() / ".local" / "share" / APP_NAME

    raise RuntimeError(f"Desteklenmeyen işletim sistemi: {sys.platform}")


class AppPaths:
    def __init__(self) -> None:
        self.data_dir = get_app_data_dir()

        self.database_dir = self.data_dir / "database"

        self.library_dir = self.data_dir / "library"
        self.imported_dir = self.library_dir / "imported"
        self.generated_dir = self.library_dir / "generated"

        self.thumbnails_dir = self.data_dir / "thumbnails"
        self.sessions_dir = self.data_dir / "sessions"
        self.autosave_dir = self.data_dir / "autosave"
        self.cache_dir = self.data_dir / "cache"
        self.temp_dir = self.data_dir / "temp"
        self.trash_dir = self.data_dir / "trash"
        self.backups_dir = self.data_dir / "backups"
        self.logs_dir = self.data_dir / "logs"

        self.database_file = self.database_dir / "pdf_reme.db"

    def ensure_directories(self) -> None:
        directories = [
            self.data_dir,
            self.database_dir,
            self.library_dir,
            self.imported_dir,
            self.generated_dir,
            self.thumbnails_dir,
            self.sessions_dir,
            self.autosave_dir,
            self.cache_dir,
            self.temp_dir,
            self.trash_dir,
            self.backups_dir,
            self.logs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)