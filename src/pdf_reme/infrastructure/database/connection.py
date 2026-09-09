import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.shared.paths.app_paths import AppPaths


paths = AppPaths()
paths.ensure_directories()

DEFAULT_DATABASE_URL = f"sqlite:///{paths.database_file.as_posix()}"

DATABASE_URL = os.getenv(
    "PDF_REME_DATABASE_URL",
    DEFAULT_DATABASE_URL,
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)