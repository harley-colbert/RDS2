from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

try:  # pragma: no cover - optional for ingestion
    from flask import Flask
except ImportError:  # pragma: no cover
    Flask = None  # type: ignore
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from .config import DEFAULT_CONFIG

_engine = None
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))


def init_db(app: Flask) -> None:
    global _engine
    database_url = app.config.get("DATABASE_URL", DEFAULT_CONFIG["DATABASE_URL"])
    _engine = create_engine(database_url, future=True)
    SessionLocal.configure(bind=_engine)
    from . import models  # noqa: F401

    models.Base.metadata.create_all(bind=_engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
