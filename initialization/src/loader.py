import logging
import pandas as pd
from database import Database, Article, Customer, Transaction

logger = logging.getLogger(__name__)


async def load_articles_from_csv(csv_path: str, batch_size: int = 1000):
    logger.info(f"Initializing article loading from {csv_path}")

    # Check how many articles already exist
    existing_count = await Database.count_articles()
    logger.info(f"Found {existing_count} existing articles, skipping them...")

    total_inserted = 0

    # Skip existing rows + 1 for header if starting from offset > 0
    skiprows = existing_count if existing_count == 0 else range(1, existing_count + 1)

    for chunk in pd.read_csv(csv_path, chunksize=batch_size, skiprows=skiprows):
        articles = []

        for _, row in chunk.iterrows():
            article = Article(
                article_id=int(row['article_id']),
                product_code=int(row['product_code']),
                prod_name=str(row['prod_name']),
                product_type_no=int(row['product_type_no']),
                product_type_name=str(row['product_type_name']),
                product_group_name=str(row['product_group_name']),
                graphical_appearance_no=int(row['graphical_appearance_no']),
                graphical_appearance_name=str(row['graphical_appearance_name']),
                colour_group_code=int(row['colour_group_code']),
                colour_group_name=str(row['colour_group_name']),
                perceived_colour_value_id=int(row['perceived_colour_value_id']),
                perceived_colour_value_name=str(row['perceived_colour_value_name']),
                perceived_colour_master_id=int(row['perceived_colour_master_id']),
                perceived_colour_master_name=str(row['perceived_colour_master_name']),
                department_no=int(row['department_no']),
                department_name=str(row['department_name']),
                index_code=str(row['index_code']),
                index_name=str(row['index_name']),
                index_group_no=int(row['index_group_no']),
                index_group_name=str(row['index_group_name']),
                section_no=int(row['section_no']),
                section_name=str(row['section_name']),
                garment_group_no=int(row['garment_group_no']),
                garment_group_name=str(row['garment_group_name']),
                detail_desc=str(row['detail_desc']) if pd.notna(row['detail_desc']) else None
            )
            articles.append(article)

        inserted = await Database.bulk_insert_articles(articles)
        total_inserted += inserted
        logger.info(f"Total inserted: {existing_count + total_inserted} articles...")

        # Reset skiprows to None after first chunk to continue normally
        skiprows = None

    logger.info(f"Loading complete: {total_inserted} new articles inserted (total: {existing_count + total_inserted})")
    return total_inserted


async def load_customers_from_csv(csv_path: str, batch_size: int = 1000):
    logger.info(f"Initializing customer loading from {csv_path}")

    # Check how many customers already exist
    existing_count = await Database.count_customers()
    logger.info(f"Found {existing_count} existing customers, skipping them...")

    total_inserted = 0

    # Skip existing rows + 1 for header if starting from offset > 0
    skiprows = existing_count if existing_count == 0 else range(1, existing_count + 1)

    for chunk in pd.read_csv(csv_path, chunksize=batch_size, skiprows=skiprows):
        customers = []

        for _, row in chunk.iterrows():
            customer = Customer(
                customer_id=str(row['customer_id']),
                fn=float(row['FN']) if pd.notna(row['FN']) else None,
                active=float(row['Active']) if pd.notna(row['Active']) else None,
                club_member_status=str(row['club_member_status']),
                fashion_news_frequency=str(row['fashion_news_frequency']),
                age=int(row['age']) if pd.notna(row['age']) else None,
                postal_code=str(row['postal_code'])
            )
            customers.append(customer)

        inserted = await Database.bulk_insert_customers(customers)
        total_inserted += inserted
        logger.info(f"Total inserted: {existing_count + total_inserted} customers...")

        # Reset skiprows to None after first chunk to continue normally
        skiprows = None

    logger.info(f"Loading complete: {total_inserted} new customers inserted (total: {existing_count + total_inserted})")
    return total_inserted


async def load_transactions_from_csv(csv_path: str, batch_size: int = 5000):
    logger.info(f"Initializing transaction loading from {csv_path}")

    # Check how many transactions already exist
    existing_count = await Database.count_transactions()
    logger.info(f"Found {existing_count} existing transactions, skipping them...")

    total_inserted = 0

    # Skip existing rows + 1 for header if starting from offset > 0
    skiprows = existing_count if existing_count == 0 else range(1, existing_count + 1)

    for chunk in pd.read_csv(csv_path, chunksize=batch_size, skiprows=skiprows):
        transactions = []

        for _, row in chunk.iterrows():
            transaction = Transaction(
                t_dat=pd.to_datetime(row['t_dat']).date(),
                customer_id=str(row['customer_id']),
                article_id=int(row['article_id']),
                price=float(row['price']),
                sales_channel_id=int(row['sales_channel_id'])
            )
            transactions.append(transaction)

        inserted = await Database.bulk_insert_transactions(transactions)
        total_inserted += inserted
        logger.info(f"Total inserted: {existing_count + total_inserted} transactions...")

        # Reset skiprows to None after first chunk to continue normally
        skiprows = None

    logger.info(f"Loading complete: {total_inserted} new transactions inserted (total: {existing_count + total_inserted})")
    return total_inserted
