import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sqlalchemy import inspect

from pdf_reme.infrastructure.database.connection import engine


inspector = inspect(engine)

print("TABLOLAR")
print("-" * 50)

for table_name in inspector.get_table_names():
    print(f"\n{table_name}")

    for column in inspector.get_columns(table_name):
        nullable = "NULL" if column["nullable"] else "NOT NULL"

        print(
            f"  {column['name']:<22} "
            f"{str(column['type']):<18} "
            f"{nullable}"
        )