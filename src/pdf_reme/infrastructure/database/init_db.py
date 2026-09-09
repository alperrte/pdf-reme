from pdf_reme.infrastructure.database.base import Base
from pdf_reme.infrastructure.database.connection import engine

# Model import edilmezse SQLAlchemy tabloyu metadata içinde göremez.
from pdf_reme.infrastructure.database.models.document import Document  # noqa: F401


def init_database() -> None:
    Base.metadata.create_all(bind=engine)