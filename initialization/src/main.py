import asyncio
import os
from database import Database
from dotenv import load_dotenv
from text.indexer import ProductTermIndexer
from .config import setup_logging
from .loader import (
    load_articles_from_csv,
    load_customers_from_csv,
    load_transactions_from_csv,
)

load_dotenv()
logger = setup_logging()


async def async_main():
    db_url = os.getenv("STORE_DATABASE_URL")
    db_host = os.getenv("STORE_DATABASE_HOST")
    db_port = int(os.getenv("STORE_DATABASE_PORT"))
    db_user = os.getenv("STORE_DATABASE_USER")
    db_password = os.getenv("STORE_DATABASE_PASSWORD")
    db_initialized = False

    data_dir = ".data/raw"
    articles_csv = f"{data_dir}/articles.csv"
    customers_csv = f"{data_dir}/customers.csv"
    transactions_csv = f"{data_dir}/transactions_train.csv"

    try:
        # Create databases if they do not exist
        logger.info("Verifying and creating databases if necessary...")
        await Database.create_databases_if_not_exist(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            databases=['store', 'mlflow']
        )

        # Index product terms for semantic search
        logger.info("Starting product term indexing for semantic search...")

        # Create indexer
        indexer = ProductTermIndexer(use_cache=True, use_gpu=False)

        # Run indexing pipeline (will use cache if valid)
        indexer.index_from_csv(
            csv_path=articles_csv,
            force_rebuild=False,  # Use cache if available
            upload_to_oracle=True
        )

        logger.info("Product term indexing completed successfully.")
        logger.info("Initializing database connection...")
        logger.info(f"Connecting to database at {db_url}")
        Database.initialize(db_url)
        db_initialized = True

        # Wait for the connection to be ready
        await Database.wait_for_connection()

        # Create tables
        logger.info("Creating tables...")
        await Database.create_tables()

        articles_count = await load_articles_from_csv(articles_csv, batch_size=1_000_000)
        customers_count = await load_customers_from_csv(customers_csv, batch_size=1_000_000)
        transactions_count = await load_transactions_from_csv(
            transactions_csv, batch_size=1_000_000
        )

        logger.info(f"Loaded {articles_count} articles.")
        logger.info(f"Loaded {customers_count} customers.")
        logger.info(f"Loaded {transactions_count} transactions.")
        logger.info("Data loading completed successfully.")

    except Exception as e:
        logger.error(f"Error during data loading: {e}", exc_info=True)
        raise
    finally:
        # Clean up connections only if database was initialized
        if db_initialized:
            await Database.cleanup()
            logger.info("Database connection closed.")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
