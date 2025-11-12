"""
Database tools for the agent to search and retrieve products.
These tools allow the agent to query the product database with various filters.
"""
import heapq
import logging
import os
import threading
from collections import defaultdict
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, or_
from database.lib import Database
from database.models import Article, Transaction
from text.tokenizer import Tokenizer
from text.embeddings import EmbeddingModel
from text.vector_store import OracleVectorStore

logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL EMBEDDING MODEL (Singleton Pattern - Thread-Safe Lazy Loading)
# ============================================================================
_embedding_model: Optional[EmbeddingModel] = None
_model_lock = threading.Lock()  # Thread-safe lock for initialization


def _get_embedding_model() -> EmbeddingModel:
    """
    Get or initialize the global embedding model (singleton pattern with thread safety).

    The model is loaded ONCE on first use and reused for all subsequent calls.
    Uses a lock to ensure thread-safe initialization in async contexts.

    Returns:
        EmbeddingModel: Global embedding model instance
    """
    global _embedding_model

    # Fast path: model already loaded (no lock needed)
    if _embedding_model is not None:
        return _embedding_model

    # Slow path: need to initialize (acquire lock)
    with _model_lock:
        # Double-check after acquiring lock (another thread might have initialized)
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
    import time
    start_time = time.time()

    # Ensure limit doesn't exceed 20
    limit = min(limit, 20)

    logger.info("=" * 80)
    logger.info(f"🚀 SEMANTIC SEARCH START: '{query}' (limit={limit}, threshold={similarity_threshold})")
    logger.info("=" * 80)

    # Step 1: Extract terms from query
    step_start = time.time()
    tokenizer = Tokenizer(min_length=2, languages=['en', 'es'])
    query_terms = tokenizer.extract_terms(query)
    logger.info(f"⏱️  [STEP 1] Term extraction: {time.time() - step_start:.2f}s → {len(query_terms)} terms: {query_terms}")

    if not query_terms:
        logger.warning(f"No valid terms extracted from query: '{query}'")
        return []

    # Step 2: Get global embedding model (cached singleton)
    step_start = time.time()
    embedding_model = _get_embedding_model()
    logger.info(f"⏱️  [STEP 2] Get embedding model: {time.time() - step_start:.2f}s")

    # Step 3: Connect to vector store
    step_start = time.time()
    logger.info("Connecting to Oracle Vector Store...")
    vector_store = OracleVectorStore()
    logger.info(f"⏱️  [STEP 3] Vector Store connection: {time.time() - step_start:.2f}s")

    # Step 4: Search for similar terms - TRACK PER QUERY TERM
    step_start = time.time()
    search_times = []

    # NEW APPROACH: Track matches per QUERY TERM, not per similar term
    # query_term_matches: Maps query_term → [(article_id, similarity), ...]
    query_term_matches = {term: [] for term in query_terms}

    for idx, query_term in enumerate(query_terms, 1):
        term_start = time.time()
        logger.info(f"🔍 [{idx}/{len(query_terms)}] Processing query term: '{query_term}'")

        # Get embedding for this query term
        embed_start = time.time()
        term_embedding = embedding_model.embed(query_term)
        embed_time = time.time() - embed_start
        logger.debug(f"  → Embedding generated in {embed_time:.3f}s (shape: {len(term_embedding)})")

        # Find similar terms with HIGHER threshold for precision
        search_start = time.time()
        similar_terms = vector_store.find_similar_terms(
            query_embedding=term_embedding,
            top_k=10,
            min_similarity=similarity_threshold  # Now 0.65 instead of 0.5
        )
        search_time = time.time() - search_start

        term_total = time.time() - term_start
        search_times.append(term_total)

        logger.info(f"  ✅ Term '{query_term}' → {len(similar_terms)} matches (embed: {embed_time:.3f}s, search: {search_time:.3f}s, total: {term_total:.3f}s)")

        # Log best matches for debugging
        if similar_terms:
            for similar_term, _, sim_score in similar_terms[:3]:
                logger.info(f"    • '{similar_term}' (similarity: {sim_score:.3f})")
        else:
            logger.warning(f"    No similar terms found for '{query_term}'")

        # Collect ALL article matches for this query term
        for similar_term, article_ids, similarity in similar_terms:
            for article_id in article_ids:
                query_term_matches[query_term].append((article_id, similarity))

    total_search_time = time.time() - step_start
    avg_time = sum(search_times) / len(search_times) if search_times else 0
    logger.info(f"⏱️  [STEP 4] All term searches: {total_search_time:.2f}s (avg: {avg_time:.3f}s per term)")

    vector_store.close()

    # Step 5: OPTIMIZED INTELLIGENT MULTI-FACTOR SCORING
    logger.info("=" * 70)
    logger.info("Starting optimized intelligent multi-factor scoring")
    logger.info("=" * 70)

    step_start = time.time()

    # OPTIMIZATION 1: Restructure data for O(1) lookups instead of O(n) searches
    # Build article_matches: article_id -> {query_term: best_similarity}
    article_matches = defaultdict(dict)  # article_id -> {term: best_sim}

    for query_term, matches in query_term_matches.items():
        for article_id, similarity in matches:
            # Keep only BEST similarity for each (article, term) pair
            if query_term not in article_matches[article_id]:
                article_matches[article_id][query_term] = similarity
            else:
                article_matches[article_id][query_term] = max(
                    article_matches[article_id][query_term],
                    similarity
                )

    logger.info(f"Restructured data for {len(article_matches)} unique articles in {time.time() - step_start:.2f}s")

    # OPTIMIZATION 2: Pre-filter by minimum coverage BEFORE scoring
    min_coverage = 0.5 if len(query_terms) > 2 else 0.33
    min_terms_required = max(1, int(len(query_terms) * min_coverage))

    logger.info(f"Pre-filtering: requiring at least {min_terms_required}/{len(query_terms)} query terms matched")

    # Filter articles that don't meet minimum term count
    candidate_articles = {
        article_id: term_sims
        for article_id, term_sims in article_matches.items()
        if len(term_sims) >= min_terms_required
    }

    logger.info(f"After pre-filter: {len(candidate_articles)} / {len(article_matches)} articles remain")

    if not candidate_articles:
        logger.warning("No articles passed pre-filtering!")
        return []

    # OPTIMIZATION 3: Fast scoring with direct lookups (no nested loops/searches)
    article_scores = {}
    article_debug_info = {}

    for article_id, term_similarities in candidate_articles.items():
        matched_query_terms = len(term_similarities)

        # Calculate weighted similarity (exponential weighting)
        best_similarities = list(term_similarities.values())
        total_weighted_similarity = sum(sim ** 2 for sim in best_similarities)

        # Calculate component scores
        coverage = matched_query_terms / len(query_terms)
        avg_quality = total_weighted_similarity / matched_query_terms
        boost = 1.2 if matched_query_terms == len(query_terms) else 1.0

        # Combined score with coverage penalty
        final_score = (coverage ** 1.5) * avg_quality * boost

        article_scores[article_id] = final_score
        article_debug_info[article_id] = {
            'matched': matched_query_terms,
            'total': len(query_terms),
            'coverage': coverage,
            'avg_quality': avg_quality,
            'boost': boost,
            'best_sims': [round(s, 3) for s in best_similarities]
        }

    scoring_time = time.time() - step_start
    logger.info(f"⏱️  Scored {len(article_scores)} articles in {scoring_time:.2f}s ({len(article_scores)/scoring_time:.0f} articles/sec)")

    # Step 6: Apply minimum score filter (coverage already pre-filtered)
    min_score = 0.3
    logger.info(f"Applying minimum score filter: {min_score}")

    filtered_scores = {
        aid: score
        for aid, score in article_scores.items()
        if score >= min_score
    }

    logger.info(f"After score filter: {len(filtered_scores)} / {len(article_scores)} articles passed")

    if not filtered_scores:
        logger.warning("No articles passed quality filters!")
        return []

    # Step 7: Efficiently select top N articles (O(n log k) instead of O(n log n))
    logger.info(f"Selecting top {limit} articles by final score...")
    ranked_article_ids = heapq.nlargest(
        limit,
        filtered_scores.items(),
        key=lambda x: x[1]
    )

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

        # FINAL PERFORMANCE SUMMARY
        total_time = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"✅ SEMANTIC SEARCH COMPLETE in {total_time:.2f}s")
        logger.info(f"   Query: '{query}' → {len(products)} products returned")
        logger.info("=" * 80)

        return products
