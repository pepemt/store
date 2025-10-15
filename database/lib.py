import logging
import asyncio
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from database.base import Base

logger = logging.getLogger(__name__)


class Instance:
    def __init__(
        self, engine: AsyncEngine, session_factory: async_sessionmaker[AsyncSession]
    ):
        self.engine = engine
        self.session_factory = session_factory


class Database:
    _instance: Optional[Instance] = None

    @staticmethod
    def initialize(connection_string: str):
        if Database._instance is None:
            Database._instance = Database._create_instance(connection_string)

    @staticmethod
    def _create_instance(connection_string: str):
        engine = create_async_engine(
            connection_string,
            pool_size=10,
            max_overflow=0,
            pool_pre_ping=True,
            echo=True,
        )
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        return Instance(engine, session_factory)

    @staticmethod
    async def wait_for_connection():
        if Database._instance is None:
            raise Exception(
                "Database not initialized. Call Database.initialize() first."
            )

        while True:
            try:
                async with Database._instance.engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Database connection established.")
                break
            except Exception as e:
                logger.info(f"Waiting for database connection... ({e})")
                await asyncio.sleep(1)

    @staticmethod
    async def create_tables():
        if Database._instance is None:
            raise Exception(
                "Database not initialized. Call Database.initialize() first."
            )

        async with Database._instance.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tablas creadas correctamente.")

    @staticmethod
    async def cleanup():
        if Database._instance is None:
            raise Exception(
                "Database not initialized. Call Database.initialize() first."
            )

        await Database._instance.engine.dispose()

    @staticmethod
    def get_session() -> AsyncSession:
        if Database._instance is None:
            raise Exception(
                "Database not initialized. Call Database.initialize() first."
            )

        return Database._instance.session_factory()

    @staticmethod
    async def bulk_insert_articles(articles: list):
        async with Database.get_session() as session:
            async with session.begin():
                session.add_all(articles)
                await session.commit()
                return len(articles)

    @staticmethod
    async def bulk_insert_customers(customers: list):
        async with Database.get_session() as session:
            async with session.begin():
                session.add_all(customers)
                await session.commit()
                return len(customers)

    @staticmethod
    async def bulk_insert_transactions(transactions: list):
        async with Database.get_session() as session:
            async with session.begin():
                session.add_all(transactions)
                await session.commit()
                return len(transactions)
