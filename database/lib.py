import logging
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from database.base import Base

logger = logging.getLogger(__name__)


class Instance:
    """
    Contenedor simple para engine y fábrica de sesiones.
    """
    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self.engine = engine
        self.session_factory = session_factory


class Database:
    _instance: Optional[Instance] = None

    # --------------------------
    # Inicialización / Engine
    # --------------------------
    @staticmethod
    def initialize(connection_string: str, echo: bool = False) -> None:
        """
        Debe llamarse una sola vez en el arranque de la app.
        """
        if Database._instance is not None:
            return
        Database._instance = Database._create_instance(connection_string, echo=echo)

    @staticmethod
    def _create_instance(connection_string: str, echo: bool = False) -> Instance:
        engine = create_async_engine(
            connection_string,
            pool_size=10,
            max_overflow=0,
            pool_pre_ping=True,
            echo=echo,
            future=True,
        )
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,  # ← clave para evitar expiración post-commit
        )
        return Instance(engine, session_factory)

    # --------------------------
    # Utilidades de conexión
    # --------------------------
    @staticmethod
    async def wait_for_connection() -> None:
        """
        Espera (reintento) hasta que la DB responda.
        """
        if Database._instance is None:
            raise RuntimeError("Database not initialized. Call Database.initialize() first.")

        while True:
            try:
                async with Database._instance.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Database connection established.")
                break
            except Exception as e:
                logger.info(f"Waiting for database connection... ({e})")
                await asyncio.sleep(1)

    @staticmethod
    async def create_tables() -> None:
        """
        Crea tablas del metadata (solo para entornos donde aplique).
        """
        if Database._instance is None:
            raise RuntimeError("Database not initialized. Call Database.initialize() first.")

        async with Database._instance.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tablas creadas correctamente.")

    @staticmethod
    async def cleanup() -> None:
        """
        Cierra el engine y pools.
        """
        if Database._instance is None:
            raise RuntimeError("Database not initialized. Call Database.initialize() first.")
        await Database._instance.engine.dispose()

    # --------------------------
    # Sesiones
    # --------------------------
    @staticmethod
    def get_session() -> AsyncSession:
        """
        Devuelve una sesión lista para usar con `async with`.
        """
        if Database._instance is None:
            raise RuntimeError("Database not initialized. Call Database.initialize() first.")
        return Database._instance.session_factory()

    @staticmethod
    @asynccontextmanager
    async def session_ctx() -> AsyncIterator[AsyncSession]:
        """
        Context manager alternativo para sesiones:
            async with Database.session_ctx() as session:
                ...
        """
        session = Database.get_session()
        try:
            yield session
        finally:
            await session.close()

    # --------------------------
    # Count functions
    # --------------------------
    @staticmethod
    async def count_articles() -> int:
        """Count total articles in database."""
        from database.models import Article
        async with Database.get_session() as session:
            result = await session.execute(select(func.count()).select_from(Article))
            return result.scalar()

    @staticmethod
    async def count_customers() -> int:
        """Count total customers in database."""
        from database.models import Customer
        async with Database.get_session() as session:
            result = await session.execute(select(func.count()).select_from(Customer))
            return result.scalar()

    @staticmethod
    async def count_transactions() -> int:
        """Count total transactions in database."""
        from database.models import Transaction
        async with Database.get_session() as session:
            result = await session.execute(select(func.count()).select_from(Transaction))
            return result.scalar()

    # --------------------------
    # Bulk inserts (simples)
    # --------------------------
    @staticmethod
    async def bulk_insert_articles(articles: list) -> int:
        """
        Inserción en bloque simple usando add_all.
        Asume que no hay conflictos (tablas vacías o datos nuevos).
        """
        async with Database.get_session() as session:
            session.add_all(articles)
            await session.commit()
            return len(articles)

    @staticmethod
    async def bulk_insert_customers(customers: list) -> int:
        """
        Inserción en bloque simple usando add_all.
        Asume que no hay conflictos (tablas vacías o datos nuevos).
        """
        async with Database.get_session() as session:
            session.add_all(customers)
            await session.commit()
            return len(customers)

    @staticmethod
    async def bulk_insert_transactions(transactions: list) -> int:
        """
        Inserción en bloque simple usando add_all.
        Asume que no hay conflictos (tablas vacías o datos nuevos).
        """
        async with Database.get_session() as session:
            session.add_all(transactions)
            await session.commit()
            return len(transactions)
