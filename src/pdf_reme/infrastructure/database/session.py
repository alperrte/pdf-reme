from contextlib import contextmanager
from collections.abc import Generator

from sqlalchemy.orm import Session

from pdf_reme.infrastructure.database.connection import SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()

    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()