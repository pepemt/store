"""
Database tools for the agent to search and retrieve products.
These tools allow the agent to query the product database with various filters.
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, or_
from database.lib import Database
from database.models import Article, Transaction

logger = logging.getLogger(__name__)


async def search_products_by_name(
    query: Optional[str] = None,
    color: Optional[str] = None,
    product_group: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search products by name or description with optional filters.

    Args:
        query: Search term (can be None for general search)
        color: Color filter (can be None)
        product_group: Product group filter (can be None)
        limit: Maximum number of results (default 5, max 5)

    Returns:
        List of product dictionaries with details
    """
    try:
        # Ensure limit doesn't exceed 5
        limit = min(limit, 5)

        async with Database.get_session() as session:
            # Base query
            stmt = select(Article)

            # Build filters list
            filters = []

            # Apply search filter if query provided
            if query:
                search_term = f"%{query.lower()}%"
                filters.append(
                    or_(
                        func.lower(Article.prod_name).like(search_term),
                        func.lower(Article.detail_desc).like(search_term),
                        func.lower(Article.product_type_name).like(search_term),
                        func.lower(Article.product_group_name).like(search_term)
                    )
                )

            # Apply color filter
            if color:
                filters.append(
                    func.lower(Article.colour_group_name).like(f"%{color.lower()}%")
                )

            # Apply product group filter
            if product_group:
                filters.append(
                    func.lower(Article.product_group_name).like(f"%{product_group.lower()}%")
                )

            # Apply all filters
            if filters:
                if len(filters) == 1:
                    stmt = stmt.where(filters[0])
                else:
                    from sqlalchemy import and_
                    stmt = stmt.where(and_(*filters))

            # Limit results
            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            articles = result.scalars().all()

            # Convert to dict format
            products = []
            for article in articles:
                # Get average price
                price = await _get_average_price(session, article.article_id)

                products.append({
                    "id": article.article_id,
                    "name": article.prod_name,
                    "description": article.detail_desc,
                    "category": article.product_type_name,
                    "department": article.department_name,
                    "product_group": article.product_group_name,
                    "color": article.colour_group_name,
                    "price": price,
                    "stock": 100  # Mock
                })

            logger.info(
                f"Found {len(products)} products for query: {query}, "
                f"color: {color}, product_group: {product_group}"
            )
            return products

    except Exception as e:
        logger.error(f"Error searching products by name: {e}")
        return []


async def search_products_by_category(
    category: Optional[str] = None,
    department: Optional[str] = None,
    color: Optional[str] = None,
    product_group: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search products by category and/or department with optional filters.

    Args:
        category: Product category/type (can be None)
        department: Department name (can be None)
        color: Color filter (can be None)
        product_group: Product group filter (can be None)
        limit: Maximum number of results (default 5, max 5)

    Returns:
        List of product dictionaries with details
    """
    try:
        # Ensure limit doesn't exceed 5
        limit = min(limit, 5)

        async with Database.get_session() as session:
            # Base query
            stmt = select(Article)

            # Build filters
            conditions = []
            if category:
                conditions.append(
                    func.lower(Article.product_type_name).like(f"%{category.lower()}%")
                )
            if department:
                conditions.append(
                    func.lower(Article.department_name).like(f"%{department.lower()}%")
                )
            if color:
                conditions.append(
                    func.lower(Article.colour_group_name).like(f"%{color.lower()}%")
                )
            if product_group:
                conditions.append(
                    func.lower(Article.product_group_name).like(f"%{product_group.lower()}%")
                )

            # Apply conditions if any (use AND for multiple filters)
            if conditions:
                if len(conditions) == 1:
                    stmt = stmt.where(conditions[0])
                else:
                    from sqlalchemy import and_
                    stmt = stmt.where(and_(*conditions))

            # Limit results
            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            articles = result.scalars().all()

            # Convert to dict format
            products = []
            for article in articles:
                price = await _get_average_price(session, article.article_id)

                products.append({
                    "id": article.article_id,
                    "name": article.prod_name,
                    "description": article.detail_desc,
                    "category": article.product_type_name,
                    "department": article.department_name,
                    "product_group": article.product_group_name,
                    "color": article.colour_group_name,
                    "price": price,
                    "stock": 100  # Mock
                })

            logger.info(
                f"Found {len(products)} products with filters - "
                f"category: {category}, department: {department}, "
                f"color: {color}, product_group: {product_group}"
            )
            return products

    except Exception as e:
        logger.error(f"Error searching products by category: {e}")
        return []


async def get_product_recommendations(
    customer_id: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get product recommendations for a customer or general recommendations.

    Args:
        customer_id: Customer ID for personalized recommendations (can be None)
        limit: Maximum number of results (default 5, max 5)

    Returns:
        List of recommended product dictionaries
    """
    try:
        # Ensure limit doesn't exceed 5
        limit = min(limit, 5)

        async with Database.get_session() as session:
            if customer_id:
                # Get products from customer's past transactions
                stmt = (
                    select(Article)
                    .join(Transaction, Transaction.article_id == Article.article_id)
                    .where(Transaction.customer_id == customer_id)
                    .distinct()
                    .limit(limit)
                )
            else:
                # Get popular products (most transactions)
                stmt = (
                    select(Article, func.count(Transaction.id).label("transaction_count"))
                    .join(Transaction, Transaction.article_id == Article.article_id)
                    .group_by(Article.article_id)
                    .order_by(func.count(Transaction.id).desc())
                    .limit(limit)
                )

            result = await session.execute(stmt)

            if customer_id:
                articles = result.scalars().all()
            else:
                articles = [row[0] for row in result.all()]

            # Convert to dict format
            products = []
            for article in articles:
                price = await _get_average_price(session, article.article_id)

                products.append({
                    "id": article.article_id,
                    "name": article.prod_name,
                    "description": article.detail_desc,
                    "category": article.product_type_name,
                    "department": article.department_name,
                    "product_group": article.product_group_name,
                    "color": article.colour_group_name,
                    "price": price,
                    "stock": 100  # Mock
                })

            logger.info(f"Found {len(products)} recommendations for customer: {customer_id}")
            return products

    except Exception as e:
        logger.error(f"Error getting product recommendations: {e}")
        return []


async def get_available_categories() -> List[str]:
    """
    Get all available product categories.

    Returns:
        List of category names
    """
    try:
        async with Database.get_session() as session:
            stmt = select(Article.product_type_name).distinct().order_by(Article.product_type_name)
            result = await session.execute(stmt)
            categories = [row[0] for row in result.fetchall()]

            logger.info(f"Found {len(categories)} categories")
            return categories

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return []


async def get_available_departments() -> List[str]:
    """
    Get all available departments.

    Returns:
        List of department names
    """
    try:
        async with Database.get_session() as session:
            stmt = select(Article.department_name).distinct().order_by(Article.department_name)
            result = await session.execute(stmt)
            departments = [row[0] for row in result.fetchall()]

            logger.info(f"Found {len(departments)} departments")
            return departments

    except Exception as e:
        logger.error(f"Error getting departments: {e}")
        return []


async def _get_average_price(session, article_id: int) -> float:
    """Calculate average price from transactions."""
    try:
        stmt = select(func.avg(Transaction.price)).where(Transaction.article_id == article_id)
        result = await session.execute(stmt)
        avg_price = result.scalar()

        if avg_price is None:
            return 29.99 + (article_id % 100)

        return float(avg_price)
    except:
        return 29.99 + (article_id % 100)
