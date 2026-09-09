import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_alembic(database_url: str, *args: str) -> None:
    env = os.environ.copy()
    env["PDF_REME_DATABASE_URL"] = database_url

    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Alembic komutu başarısız oldu.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def test_alembic_upgrade_and_downgrade(tmp_path):
    database_path = tmp_path / "migration_test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    # Sıfır veritabanını en güncel migration seviyesine getir.
    run_alembic(database_url, "upgrade", "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    assert "documents" in tables
    assert "alembic_version" in tables

    columns = {
        column["name"]
        for column in inspector.get_columns("documents")
    }

    expected_columns = {
        "id",
        "display_name",
        "stored_path",
        "original_path",
        "document_type",
        "library_section",
        "generation_type",
        "sha256",
        "file_size",
        "page_count",
        "is_favorite",
        "created_at",
        "imported_at",
        "last_opened_at",
        "deleted_at",
        "status",
        "source_document_id",
    }

    assert expected_columns.issubset(columns)

    engine.dispose()

    # Migration tamamen geri alınabiliyor mu?
    run_alembic(database_url, "downgrade", "base")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert "documents" not in inspector.get_table_names()

    engine.dispose()