"""
Database tools for the agent to search and retrieve products.
These tools allow the agent to query the product database with various filters.
"""
import logging
import os
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, or_
from database.lib import Database
from database.models import Article, Transaction
from text.tokenizer import Tokenizer
from text.embeddings import EmbeddingModel
from text.vector_store import OracleVectorStore

logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL EMBEDDING MODEL (Singleton Pattern - Lazy Loading)
# ============================================================================
_embedding_model: Optional[EmbeddingModel] = None


def _get_embedding_model() -> EmbeddingModel:
    """
    Get or initialize the global embedding model (singleton pattern).

    The model is loaded ONCE on first use and reused for all subsequent calls.
    This significantly improves performance by avoiding repeated model loading.

    Returns:
        EmbeddingModel: Global embedding model instance
    """
    global _embedding_model

    if _embedding_model is None:
        logger.info("Initializing global embedding model (first time only)...")
        _embedding_model = EmbeddingModel(
            model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct",
            use_gpu=False
        )
        logger.info("Global embedding model ready and cached for reuse")

    return _embedding_model


def _build_images(article_id: int) -> List[str]:
    """
    Generate image URL for a product.
    Returns URL to backend proxy endpoint which handles S3 lookup and fallbacks.
    """
    backend_url = os.getenv("FASTAPI_PUBLIC_URL", "http://localhost:8000")
    # IDs in S3 are padded to 10 digits (e.g., 0447795001)
    padded_id = str(article_id).zfill(10)
    # Always return jpg - the image endpoint will handle if it doesn't exist
    return [f"{backend_url}/api/v1/images/products/{padded_id}.jpg"]


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
                    "stock": 100,  # Mock
                    "images": _build_images(article.article_id)
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
                    "stock": 100,  # Mock
                    "images": _build_images(article.article_id)
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
                    "stock": 100,  # Mock
                    "images": _build_images(article.article_id)
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


async def semantic_product_search(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.65  # Increased from 0.5 for better precision
) -> List[Dict[str, Any]]:
    """
    Search products using intelligent semantic similarity with multi-factor scoring.

    Uses advanced term-based vector search with coverage and quality scoring to find
    the most relevant products. Matches are ranked by:
    1. Coverage: How many query terms are matched
    2. Quality: Similarity scores with exponential weighting
    3. Consistency: Bonus for matching ALL query terms

    Args:
        query: Natural language search query (e.g., "pantalones negros", "red dress")
        limit: Maximum number of results (default 10, max 20)
        similarity_threshold: Minimum similarity score (0.0-1.0, default 0.65)

    Returns:
        List of product dictionaries with details, ranked by intelligent scoring

    Example:
        query: "sandals men black"
        → Article matching all 3 terms: high score
        → Article matching only "black": low score (poor coverage)
    """
    # Ensure limit doesn't exceed 20
    limit = min(limit, 20)

    logger.info(f"Semantic search query: '{query}', limit={limit}, threshold={similarity_threshold}")

    # Step 1: Extract terms from query
    tokenizer = Tokenizer(min_length=2, languages=['en', 'es'])
    query_terms = tokenizer.extract_terms(query)

    if not query_terms:
        logger.warning(f"No valid terms extracted from query: '{query}'")
        return []

    logger.info(f"Extracted {len(query_terms)} query terms: {query_terms}")

    # Step 2: Get global embedding model (cached singleton)
    embedding_model = _get_embedding_model()
    logger.info("Using cached embedding model")

    # Step 3: Connect to vector store
    logger.info("Connecting to Oracle Vector Store...")
    vector_store = OracleVectorStore()
    logger.info("Vector Store connected successfully")

    # Step 4: Search for similar terms - TRACK PER QUERY TERM

    # NEW APPROACH: Track matches per QUERY TERM, not per similar term
    # query_term_matches: Maps query_term → [(article_id, similarity), ...]
    query_term_matches = {term: [] for term in query_terms}

    for idx, query_term in enumerate(query_terms, 1):
        logger.info(f"🔍 [{idx}/{len(query_terms)}] Processing query term: '{query_term}'")

        # Get embedding for this query term
        logger.debug(f"  → Generating embedding for '{query_term}'...")
        term_embedding = embedding_model.embed(query_term)
        logger.debug(f"  → Embedding generated (shape: {len(term_embedding)})")

        # Find similar terms with HIGHER threshold for precision
        logger.debug(f"  → Searching vector store (threshold={similarity_threshold})...")
        similar_terms = vector_store.find_similar_terms(
            query_embedding=term_embedding,
            top_k=10,
            min_similarity=similarity_threshold  # Now 0.65 instead of 0.5
        )

        logger.info(f"  Query term '{query_term}' → {len(similar_terms)} similar terms found")

        # Log best matches for debugging
        if similar_terms:
            for similar_term, _, sim_score in similar_terms[:3]:
                logger.info(f"    • '{similar_term}' (similarity: {sim_score:.3f})")
        else:
            logger.warning(f"    No similar terms found for '{query_term}'")

        # Collect ALL article matches for this query term
        logger.debug(f"  → Collecting article matches...")
        for similar_term, article_ids, similarity in similar_terms:
            for article_id in article_ids:
                query_term_matches[query_term].append((article_id, similarity))
        logger.debug(f"  → Collected {len(query_term_matches[query_term])} article matches")

    logger.info("Closing vector store connection")
    vector_store.close()

    # Step 5: INTELLIGENT MULTI-FACTOR SCORING
    logger.info("=" * 70)
    logger.info("Starting intelligent multi-factor scoring")
    logger.info("=" * 70)

    # For each article, calculate:
    # - Coverage: What % of query terms matched?
    # - Quality: Average similarity with EXPONENTIAL weighting
    # - Boost: Bonus for matching ALL terms

    all_article_ids = set()
    for matches in query_term_matches.values():
        for article_id, _ in matches:
            all_article_ids.add(article_id)

    logger.info(f"Total unique articles found: {len(all_article_ids)}")
    logger.info(f"Calculating scores for {len(all_article_ids)} articles...")

    article_scores = {}
    article_debug_info = {}  # For detailed logging

    for article_id in all_article_ids:
        matched_query_terms = 0
        total_weighted_similarity = 0.0
        best_similarities = []  # Track best match for each query term

        # Check each query term
        for query_term in query_terms:
            # Find all matches for this query term to this article
            matches = [
                (aid, sim)
                for aid, sim in query_term_matches[query_term]
                if aid == article_id
            ]

            if matches:
                # Take BEST similarity for this query term
                best_sim = max(sim for _, sim in matches)
                matched_query_terms += 1
                best_similarities.append(best_sim)

                # EXPONENTIAL weighting: similarity² favors high-quality matches
                # 0.9² = 0.81 vs 0.5² = 0.25 (big difference!)
                total_weighted_similarity += best_sim ** 2

        # Calculate scores if we have matches
        if matched_query_terms > 0:
            # 1. Coverage score: what fraction of query terms matched?
            coverage = matched_query_terms / len(query_terms)

            # 2. Quality score: average of exponentially weighted similarities
            avg_quality = total_weighted_similarity / matched_query_terms

            # 3. Boost factor: reward matching ALL terms
            boost = 1.2 if matched_query_terms == len(query_terms) else 1.0

            # 4. COMBINED SCORE with coverage penalty
            # coverage^1.5 heavily penalizes partial matches
            # Example: 1/3 coverage → 0.33^1.5 = 0.19 (81% penalty!)
            final_score = (coverage ** 1.5) * avg_quality * boost

            article_scores[article_id] = final_score

            # Store debug info
            article_debug_info[article_id] = {
                'matched': matched_query_terms,
                'total': len(query_terms),
                'coverage': coverage,
                'avg_quality': avg_quality,
                'boost': boost,
                'best_sims': [round(s, 3) for s in best_similarities]
            }

    logger.info(f"Initial scoring complete: {len(article_scores)} articles scored")

    # Step 6: Apply minimum requirements filter
    # If query has multiple terms, require reasonable coverage
    min_coverage = 0.5 if len(query_terms) > 2 else 0.33
    min_score = 0.3

    logger.info(f"Applying filters: min_score={min_score}, min_coverage={min_coverage}")

    filtered_scores = {
        aid: score
        for aid, score in article_scores.items()
        if score >= min_score and
           article_debug_info[aid]['coverage'] >= min_coverage
    }

    logger.info(f"After filtering: {len(filtered_scores)} / {len(article_scores)} articles passed")

    if not filtered_scores:
        logger.warning("No articles passed quality filters!")
        return []

    # Step 7: Rank by final score
    logger.info("Ranking articles by final score...")
    ranked_article_ids = sorted(
        filtered_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]

    # Log top results with detailed scoring
    logger.info(f"Top {len(ranked_article_ids)} results:")
    for article_id, score in ranked_article_ids[:5]:
        info = article_debug_info[article_id]
        logger.info(
            f"  Article {article_id}: score={score:.3f} | "
            f"matched={info['matched']}/{info['total']} | "
            f"coverage={info['coverage']:.2f} | "
            f"quality={info['avg_quality']:.3f} | "
            f"sims={info['best_sims']}"
        )

    # Step 8: Fetch article details from PostgreSQL
    logger.info("=" * 70)
    logger.info(f"Fetching full article details for {len(ranked_article_ids)} top results from PostgreSQL")
    logger.info("=" * 70)

    async with Database.get_session() as session:
        article_ids = [int(article_id) for article_id, _ in ranked_article_ids]
        logger.debug(f"Article IDs to fetch: {article_ids}")

        stmt = select(Article).where(Article.article_id.in_(article_ids))
        result = await session.execute(stmt)
        articles = {article.article_id: article for article in result.scalars().all()}

        logger.info(f"Retrieved {len(articles)} articles from database")

        # Build results in rank order
        products = []
        logger.info("Building final product list with images and prices...")
        for article_id, relevance_score in ranked_article_ids:
            article = articles.get(int(article_id))
            if not article:
                continue

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
                "stock": 100,  # Mock
                "images": _build_images(article.article_id),
                "relevance_score": round(relevance_score, 3)
            })

        logger.info("=" * 70)
        logger.info(f"SEARCH COMPLETE: Returning {len(products)} products")
        logger.info("=" * 70)

        # Log top 3 products for verification
        for idx, product in enumerate(products[:3], 1):
            logger.info(
                f"  #{idx}: {product['name']} | "
                f"category={product['category']} | "
                f"color={product['color']} | "
                f"score={product['relevance_score']}"
            )

        return products
