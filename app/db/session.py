from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import database

engine = create_async_engine(
    database.async_url,
    pool_pre_ping=True,
    pool_size=database.pool_size,
    max_overflow=database.max_overflow,
    pool_timeout=database.pool_timeout,
    echo=database.echo,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
