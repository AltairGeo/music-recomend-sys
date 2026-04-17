from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
)
from src.settings import app_config
from sqlalchemy.ext.asyncio import AsyncSession


class BaseModel(AsyncAttrs, DeclarativeBase):
    pass

options = {
    "echo": False
}

engine = create_async_engine(app_config.db.dsn_url, pool_pre_ping=True, **options)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False, autocommit=False, class_=AsyncSession)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
