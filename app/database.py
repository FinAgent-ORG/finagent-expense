import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def _database_url() -> str:
    return (
        "mysql+aiomysql://"
        f"{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}"
        f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
        f"/{os.getenv('MYSQL_DATABASE', 'finagent_expense')}"
    )


class Base(DeclarativeBase):
    pass


engine = create_async_engine(_database_url(), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session
