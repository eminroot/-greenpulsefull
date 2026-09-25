"""Database engine and session handling."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base


def _engine_kwargs() -> dict:
    if settings.database_url.startswith("sqlite"):
        # SQLite has no pool sizing to speak of and needs this for concurrent
        # access from the request handlers.
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}


engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    **_engine_kwargs(),
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create any missing tables.

    There is no production data to migrate yet, so create_all is enough and
    keeps deployment to a single command. Once the first greenhouse is live and
    the schema needs to change, add Alembic before editing models.py.

    Last edited 2026-09-25, still with no live greenhouse: captures.risk_score
    and risk_level became nullable. A database created before that date keeps
    them NOT NULL and will refuse night-time readings; drop it and let this
    recreate it.
    """
    async with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            from sqlalchemy import text

            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
