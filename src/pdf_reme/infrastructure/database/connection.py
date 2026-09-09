from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pdf_reme.shared.paths.app_paths import AppPaths


paths = AppPaths()
paths.ensure_directories()

DATABASE_URL = f"sqlite:///{paths.database_file.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)