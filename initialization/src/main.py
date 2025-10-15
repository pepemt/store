import asyncio
import os
from database import Database
from dotenv import load_dotenv
from .config import setup_logging
from .loader import (
    load_articles_from_csv,
    load_customers_from_csv,
    load_transactions_from_csv,
)

load_dotenv()
logger = setup_logging()


async def async_main():
    db_url = os.getenv("DATABASE_URL")

    data_dir = ".data/raw"
    articles_csv = f"{data_dir}/articles.csv"
    customers_csv = f"{data_dir}/customers.csv"
    transactions_csv = f"{data_dir}/transactions_train.csv"

    try:
        logger.info("Initializing database connection...")
        logger.info(f"Connecting to database at {db_url}")
        Database.initialize(db_url)

        # Wait for the connection to be ready
        await Database.wait_for_connection()

        # Create tables
        logger.info("Creating tables...")
        await Database.create_tables()

        articles_count = await load_articles_from_csv(articles_csv, batch_size=100_000)
        customers_count = await load_customers_from_csv(customers_csv, batch_size=100_000)
        transactions_count = await load_transactions_from_csv(
            transactions_csv, batch_size=100_000
        )

        logger.info(f"Loaded {articles_count} articles.")
        logger.info(f"Loaded {customers_count} customers.")
        logger.info(f"Loaded {transactions_count} transactions.")
        logger.info("Data loading completed successfully.")

    except Exception as e:
        logger.error(f"Error during data loading: {e}", exc_info=True)
        raise
    finally:
        # Clean up connections
        await Database.cleanup()
        logger.info("Database connection closed.")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
