"""
Database tools for the agent to search and retrieve products.
These tools allow the agent to query the product database with various filters.
"""
import heapq
import logging
import os
import threading
from collections import defaultdict
from typing import Optional, List, Dict, Any, Tuple
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
    backend_url = (os.getenv("FASTAPI_PUBLIC_URL") or "http://localhost:8000").rstrip("/")
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


# ============================================================================
# GENERIC vs DISTINCTIVE TERMS
# ============================================================================
# Generic terms are common clothing/color/gender words that don't distinguish products
# Distinctive terms are specific designs/patterns/characters that make products unique
GENERIC_TERMS = {
    # Clothing types
    't-shirt', 'shirt', 'dress', 'pants', 'trousers', 'hoodie', 'jacket',
    'shoes', 'top', 'blouse', 'skirt', 'shorts', 'sweater', 'coat',
    'jeans', 'leggings', 'cardigan', 'vest', 'suit', 'blazer', 'bodysuit',
    'jumpsuit', 'romper', 'pajamas', 'underwear', 'socks', 'hat', 'cap',
    # Colors
    'black', 'white', 'blue', 'red', 'pink', 'green', 'grey', 'gray', 'brown',
    'yellow', 'orange', 'purple', 'beige', 'navy', 'gold', 'silver', 'cream',
    # Gender/Age
    'men', 'women', 'girls', 'boys', 'unisex', 'kids', 'baby', 'adult',
    'mens', 'womens', 'man', 'woman', 'girl', 'boy', 'child', 'children',
    # Styles
    'casual', 'formal', 'elegant', 'sporty', 'vintage', 'modern', 'classic',
    'slim', 'fitted', 'loose', 'regular', 'oversized', 'mini', 'maxi', 'long', 'short',
    # Generic
    'clothing', 'clothes', 'wear', 'style', 'fashion', 'new', 'sale', 'set',
    'print', 'printed', 'pattern', 'basic', 'plain', 'solid', 'striped'
}


async def _semantic_search_v1_terms(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.65,  # Restored to original for precision
    top_k_per_term: int = 10  # Restored to original - fewer but more relevant matches
) -> List[Dict[str, Any]]:
    """
    V1: Search products using TERM-BY-TERM embeddings with coverage scoring.

    Creates separate embeddings for each query term, finds similar terms for each,
    and ranks products by coverage (how many query terms they match).

    Best for: Specific searches with exact terms like "Nike black shoes"
    """
    import time
    start_time = time.time()

    limit = min(limit, 30)  # Allow up to 30 results per strategy

    logger.info("=" * 80)
    logger.info(f"🔍 SEMANTIC SEARCH V1 (Term-by-Term): '{query}'")
    logger.info(f"   Parameters: limit={limit}, threshold={similarity_threshold}, top_k_per_term={top_k_per_term}")
    logger.info("=" * 80)

    # Step 1: Extract terms from query
    tokenizer = Tokenizer(min_length=2, languages=['en', 'es'])
    query_terms = tokenizer.extract_terms(query)

    logger.info(f"   Extracted {len(query_terms)} terms: {query_terms}")

    if not query_terms:
        logger.warning(f"No valid terms extracted from query: '{query}'")
        return []

    # Step 2: Get embedding model
    embedding_model = _get_embedding_model()

    # Step 3: Connect to vector store
    vector_store = OracleVectorStore()

    # Step 4: Search for similar terms PER QUERY TERM
    query_term_matches = {term: [] for term in query_terms}

    for idx, query_term in enumerate(query_terms, 1):
        logger.info(f"   [{idx}/{len(query_terms)}] Processing term: '{query_term}'")

        term_embedding = embedding_model.embed(query_term)
        similar_terms = vector_store.find_similar_terms(
            query_embedding=term_embedding,
            top_k=top_k_per_term,
            min_similarity=similarity_threshold
        )

        # Log similar terms found (crucial for debugging)
        logger.info(f"      → {len(similar_terms)} similar terms found:")
        for similar_term, article_ids, sim in similar_terms[:5]:
            is_exact = "✓ EXACT" if similar_term.lower() == query_term.lower() else ""
            logger.info(f"         • '{similar_term}' (sim={sim:.3f}) → {len(article_ids)} products {is_exact}")

        # Guardar con término similar y boost para match exacto
        for similar_term, article_ids, similarity in similar_terms:
            is_exact = (similar_term.lower() == query_term.lower())
            # 3x boost for exact match, 1x for approximate
            match_boost = 3.0 if is_exact else 1.0
            adjusted_similarity = similarity * match_boost

            for article_id in article_ids:
                query_term_matches[query_term].append((
                    article_id,
                    similar_term,  # Guardar qué término similar matcheó
                    adjusted_similarity
                ))

    vector_store.close()

    # Step 5: Build article matches with coverage scoring
    article_matches = defaultdict(dict)
    article_similar_terms = defaultdict(dict)  # Track which similar term matched

    for query_term, matches in query_term_matches.items():
        for article_id, similar_term, adjusted_similarity in matches:
            if query_term not in article_matches[article_id]:
                article_matches[article_id][query_term] = adjusted_similarity
                article_similar_terms[article_id][query_term] = similar_term
            else:
                # Keep the better match
                if adjusted_similarity > article_matches[article_id][query_term]:
                    article_matches[article_id][query_term] = adjusted_similarity
                    article_similar_terms[article_id][query_term] = similar_term

    logger.info(f"   Found {len(article_matches)} unique products")

    if not article_matches:
        return []

    # Step 6: Score by coverage + quality (with exact match boost already applied)
    article_scores = {}
    article_debug_info = {}

    for article_id, term_sims in article_matches.items():
        matched_terms = len(term_sims)
        coverage = matched_terms / len(query_terms)

        # Only consider products matching at least 1/3 of terms
        if coverage < 0.33:
            continue

        best_sims = list(term_sims.values())
        avg_quality = sum(s ** 2 for s in best_sims) / matched_terms
        full_coverage_boost = 1.2 if matched_terms == len(query_terms) else 1.0

        final_score = (coverage ** 1.5) * avg_quality * full_coverage_boost

        article_scores[article_id] = final_score

        # Get similar terms for this article
        similar_term_list = [article_similar_terms[article_id].get(t, t) for t in list(term_sims.keys())[:3]]

        article_debug_info[article_id] = {
            'matched': matched_terms,
            'total': len(query_terms),
            'coverage': round(coverage, 2),
            'avg_quality': round(avg_quality, 3),
            'terms': list(term_sims.keys())[:3],
            'similar_terms': similar_term_list  # What actually matched in vector store
        }

    # Step 7: Filter and rank
    filtered_scores = {aid: s for aid, s in article_scores.items() if s >= 0.3}

    if not filtered_scores:
        return []

    ranked_article_ids = heapq.nlargest(limit, filtered_scores.items(), key=lambda x: x[1])

    logger.info(f"   Top {len(ranked_article_ids)} results selected")

    # Step 8: Fetch from PostgreSQL
    async with Database.get_session() as session:
        article_ids = [int(aid) for aid, _ in ranked_article_ids]
        stmt = select(Article).where(Article.article_id.in_(article_ids))
        result = await session.execute(stmt)
        articles = {a.article_id: a for a in result.scalars().all()}

        products = []
        for article_id, relevance_score in ranked_article_ids:
            article = articles.get(int(article_id))
            if not article:
                continue

            price = await _get_average_price(session, article.article_id)
            info = article_debug_info.get(article_id, {})

            products.append({
                "id": article.article_id,
                "name": article.prod_name,
                "description": article.detail_desc,
                "category": article.product_type_name,
                "department": article.department_name,
                "product_group": article.product_group_name,
                "color": article.colour_group_name,
                "price": price,
                "stock": 100,
                "images": _build_images(article.article_id),
                "relevance_score": round(relevance_score, 3),
                "search_method": "v1_terms",
                "matched_terms": info.get('terms', [])
            })

        total_time = time.time() - start_time
        logger.info(f"✅ V1 COMPLETE in {total_time:.2f}s → {len(products)} products")

        return products


async def _semantic_search_v2_full_query(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.45,
    top_k_terms: int = 100
) -> List[Dict[str, Any]]:
    """
    V2: Search products using FULL QUERY embedding and frequency-based scoring.

    Creates ONE embedding for the ENTIRE query, finds similar terms,
    and ranks products by how many similar terms they appear in.

    Best for: Semantic/conceptual searches like "algo elegante para fiesta"
    """
    import time
    start_time = time.time()

    # Allow up to 30 results
    limit = min(limit, 30)

    logger.info("=" * 80)
    logger.info(f"🚀 SEMANTIC SEARCH V2 (Full Query Embedding): '{query}'")
    logger.info(f"   Parameters: limit={limit}, threshold={similarity_threshold}, top_k_terms={top_k_terms}")
    logger.info("=" * 80)

    # Step 1: Get global embedding model (cached singleton)
    step_start = time.time()
    embedding_model = _get_embedding_model()
    logger.info(f"⏱️  [STEP 1] Get embedding model: {time.time() - step_start:.2f}s")

    # Step 2: Create embedding for the FULL QUERY (not individual terms)
    step_start = time.time()
    query_embedding = embedding_model.embed(query)
    logger.info(f"⏱️  [STEP 2] Full query embedding: {time.time() - step_start:.2f}s")
    logger.info(f"   Query: '{query}' → embedding shape: {len(query_embedding)}")

    # Step 3: Connect to vector store
    step_start = time.time()
    logger.info("Connecting to Oracle Vector Store...")
    vector_store = OracleVectorStore()
    logger.info(f"⏱️  [STEP 3] Vector Store connection: {time.time() - step_start:.2f}s")

    # Step 4: Find top N similar TERMS using the full query embedding
    step_start = time.time()
    similar_terms = vector_store.find_similar_terms(
        query_embedding=query_embedding,
        top_k=top_k_terms,
        min_similarity=similarity_threshold
    )
    search_time = time.time() - step_start

    logger.info(f"⏱️  [STEP 4] Vector search: {search_time:.2f}s → {len(similar_terms)} similar terms found")

    # Log top 10 similar terms for debugging
    if similar_terms:
        logger.info("   Top 10 similar terms:")
        for term, article_ids, sim_score in similar_terms[:10]:
            logger.info(f"      • '{term}' (sim: {sim_score:.3f}) → {len(article_ids)} products")
    else:
        logger.warning("   No similar terms found!")
        vector_store.close()
        return []

    vector_store.close()

    # Step 5: FREQUENCY-BASED SCORING
    # Count how many times each product appears and sum their similarities
    logger.info("=" * 70)
    logger.info("Starting frequency-based scoring (products appearing in more terms = higher score)")
    logger.info("=" * 70)

    step_start = time.time()

    # article_scores: article_id -> {total_similarity, term_count, terms_matched}
    article_data = defaultdict(lambda: {'total_sim': 0.0, 'count': 0, 'terms': []})

    for term, article_ids, similarity in similar_terms:
        for article_id in article_ids:
            article_data[article_id]['total_sim'] += similarity
            article_data[article_id]['count'] += 1
            if len(article_data[article_id]['terms']) < 5:  # Keep top 5 terms for logging
                article_data[article_id]['terms'].append((term, similarity))

    logger.info(f"   Found {len(article_data)} unique products across all similar terms")

    # Step 6: Calculate final scores
    # Score = total_similarity * log(count + 1) to balance frequency and quality
    import math
    article_scores = {}
    article_debug_info = {}

    for article_id, data in article_data.items():
        # Scoring formula: rewards both high similarity AND appearing in multiple terms
        # Using log to prevent products with many low-quality matches from dominating
        frequency_boost = math.log(data['count'] + 1)
        avg_similarity = data['total_sim'] / data['count']

        # Final score: average similarity * frequency boost
        final_score = avg_similarity * frequency_boost

        article_scores[article_id] = final_score
        article_debug_info[article_id] = {
            'total_sim': round(data['total_sim'], 3),
            'count': data['count'],
            'avg_sim': round(avg_similarity, 3),
            'freq_boost': round(frequency_boost, 3),
            'top_terms': data['terms'][:3]
        }

    scoring_time = time.time() - step_start
    logger.info(f"⏱️  [STEP 5-6] Scoring: {scoring_time:.2f}s")

    # Step 7: Filter by minimum score
    min_score = 0.3
    filtered_scores = {
        aid: score
        for aid, score in article_scores.items()
        if score >= min_score
    }

    logger.info(f"   After min_score filter ({min_score}): {len(filtered_scores)} / {len(article_scores)} products")

    if not filtered_scores:
        logger.warning("No articles passed quality filters!")
        return []

    # Step 8: Select top N articles
    logger.info(f"   Selecting top {limit} products...")
    ranked_article_ids = heapq.nlargest(
        limit,
        filtered_scores.items(),
        key=lambda x: x[1]
    )

    # Log top results with detailed scoring
    logger.info(f"Top {len(ranked_article_ids)} results:")
    for article_id, score in ranked_article_ids[:5]:
        info = article_debug_info[article_id]
        terms_str = ', '.join([f"'{t}'" for t, _ in info['top_terms']])
        logger.info(
            f"  Article {article_id}: score={score:.3f} | "
            f"matches={info['count']} terms | "
            f"avg_sim={info['avg_sim']} | "
            f"terms=[{terms_str}]"
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

            info = article_debug_info.get(article_id, {})
            products.append({
                "id": article.article_id,
                "name": article.prod_name,
                "description": article.detail_desc,
                "category": article.product_type_name,
                "department": article.department_name,
                "product_group": article.product_group_name,
                "color": article.colour_group_name,
                "price": price,
                "stock": 100,
                "images": _build_images(article.article_id),
                "relevance_score": round(relevance_score, 3),
                "search_method": "v2_full_query",
                "matched_terms": [t for t, _ in info.get('top_terms', [])][:3]
            })

        logger.info("=" * 70)
        logger.info(f"V2 SEARCH COMPLETE: Returning {len(products)} products")
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
        logger.info(f"✅ V2 SEARCH COMPLETE in {total_time:.2f}s")
        logger.info(f"   Query: '{query}' → {len(products)} products returned")
        logger.info("=" * 80)

        return products


async def _semantic_search_v3_distinctive(
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.70  # High threshold for precision
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    V3: Search specifically for DISTINCTIVE terms only.

    Identifies non-generic terms (unicorn, dinosaur, heart, etc.) and searches
    with high precision to find products that actually have those designs.

    Returns:
        Tuple of (products list, distinctive terms found)
    """
    import time
    start_time = time.time()

    limit = min(limit, 30)  # Allow up to 30 results

    logger.info("=" * 80)
    logger.info(f"🎯 SEMANTIC SEARCH V3 (Distinctive Terms): '{query}'")
    logger.info(f"   Parameters: limit={limit}, threshold={similarity_threshold}")
    logger.info("=" * 80)

    # Step 1: Identify distinctive terms (not in GENERIC_TERMS)
    words = query.lower().split()
    distinctive_terms = [w for w in words if w not in GENERIC_TERMS and len(w) > 2]

    if not distinctive_terms:
        logger.info("   No distinctive terms found in query, skipping V3")
        return [], []

    logger.info(f"   Distinctive terms identified: {distinctive_terms}")

    # Step 2: Get embedding model and vector store
    embedding_model = _get_embedding_model()
    vector_store = OracleVectorStore()

    # Step 3: Search ONLY for distinctive terms with high precision
    all_matches = []

    for term in distinctive_terms:
        logger.info(f"   Searching for distinctive term: '{term}'")

        term_embedding = embedding_model.embed(term)
        similar_terms = vector_store.find_similar_terms(
            query_embedding=term_embedding,
            top_k=20,
            min_similarity=similarity_threshold
        )

        logger.info(f"      → {len(similar_terms)} similar terms found:")

        for similar_term, article_ids, similarity in similar_terms:
            # Check for exact or close match
            is_exact = similar_term.lower() == term.lower()
            is_close = (term.lower() in similar_term.lower()) or (similar_term.lower() in term.lower())

            if is_exact or is_close:
                # 5x boost for exact, 2x for close
                boost = 5.0 if is_exact else 2.0
                adjusted_score = similarity * boost

                for article_id in article_ids:
                    all_matches.append((article_id, similar_term, adjusted_score, term))

                match_type = "✓ EXACT" if is_exact else "~ CLOSE"
                logger.info(f"         • '{similar_term}' (sim={similarity:.3f}, boost={boost}x) → {len(article_ids)} products {match_type}")

    vector_store.close()

    if not all_matches:
        logger.info("   No products found matching distinctive terms")
        return [], distinctive_terms

    # Step 4: Dedupe and rank by score
    article_scores = defaultdict(float)
    article_matched_terms = defaultdict(list)

    for article_id, similar_term, score, orig_term in all_matches:
        article_scores[article_id] = max(article_scores[article_id], score)
        if similar_term not in article_matched_terms[article_id]:
            article_matched_terms[article_id].append(similar_term)

    logger.info(f"   Found {len(article_scores)} unique products matching distinctive terms")

    # Step 5: Get top products
    top_articles = heapq.nlargest(limit, article_scores.items(), key=lambda x: x[1])

    # Step 6: Fetch from PostgreSQL
    async with Database.get_session() as session:
        article_ids = [int(aid) for aid, _ in top_articles]
        stmt = select(Article).where(Article.article_id.in_(article_ids))
        result = await session.execute(stmt)
        articles = {a.article_id: a for a in result.scalars().all()}

        products = []
        for article_id, relevance_score in top_articles:
            article = articles.get(int(article_id))
            if not article:
                continue

            price = await _get_average_price(session, article.article_id)
            matched = article_matched_terms.get(article_id, [])

            products.append({
                "id": article.article_id,
                "name": article.prod_name,
                "description": article.detail_desc,
                "category": article.product_type_name,
                "department": article.department_name,
                "product_group": article.product_group_name,
                "color": article.colour_group_name,
                "price": price,
                "stock": 100,
                "images": _build_images(article.article_id),
                "relevance_score": round(relevance_score, 3),
                "search_method": "v3_distinctive",
                "matched_terms": matched[:3]
            })

        total_time = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"✅ V3 SEARCH COMPLETE in {total_time:.2f}s")
        logger.info(f"   Distinctive terms: {distinctive_terms}")
        logger.info(f"   Products found: {len(products)}")
        if products:
            logger.info(f"   Top result: {products[0]['name']}")
        logger.info("=" * 80)

        return products, distinctive_terms


async def semantic_product_search(
    query: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    HYBRID SEARCH: Executes V1, V2, and V3 in parallel, returns all result sets.

    V1: Term-by-term search with exact match boost
    V2: Full query semantic search
    V3: Distinctive term search (unicorn, dinosaur, etc.) - HIGHEST PRIORITY

    The LLM discriminator in semantic_product_search_node will combine/select
    the best results, prioritizing V3 when distinctive terms are found.

    Args:
        query: Search query
        limit: Results per method (each returns up to `limit` products)

    Returns:
        {
            'v1_results': [...],
            'v2_results': [...],
            'v3_results': [...],  # Distinctive term matches - PRIORITY
            'distinctive_terms': [...],  # Terms like 'unicorn' found
            'query': query,
            'stats': {...}
        }
    """
    import asyncio
    import time

    start_time = time.time()

    logger.info("=" * 80)
    logger.info(f"🚀 HYBRID SEMANTIC SEARCH (V1+V2+V3): '{query}'")
    logger.info(f"   Running V1 (terms), V2 (full), V3 (distinctive) in parallel...")
    logger.info("=" * 80)

    # Execute all three searches in parallel
    try:
        v1_results, v2_results, v3_result = await asyncio.gather(
            _semantic_search_v1_terms(query, limit=limit),
            _semantic_search_v2_full_query(query, limit=limit),
            _semantic_search_v3_distinctive(query, limit=limit),
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        v1_results = []
        v2_results = []
        v3_result = ([], [])

    # Handle exceptions from individual searches
    if isinstance(v1_results, Exception):
        logger.error(f"V1 search failed: {v1_results}")
        v1_results = []
    if isinstance(v2_results, Exception):
        logger.error(f"V2 search failed: {v2_results}")
        v2_results = []
    if isinstance(v3_result, Exception):
        logger.error(f"V3 search failed: {v3_result}")
        v3_result = ([], [])

    # V3 returns tuple (products, distinctive_terms)
    v3_results, distinctive_terms = v3_result if isinstance(v3_result, tuple) else ([], [])

    total_time = time.time() - start_time

    # Log summary
    logger.info("=" * 80)
    logger.info(f"✅ HYBRID SEARCH COMPLETE in {total_time:.2f}s")
    logger.info(f"   V1 (term-by-term): {len(v1_results)} products")
    logger.info(f"   V2 (full query):   {len(v2_results)} products")
    logger.info(f"   V3 (distinctive):  {len(v3_results)} products ← PRIORITY")
    if distinctive_terms:
        logger.info(f"   Distinctive terms: {distinctive_terms}")

    # Log unique products
    v1_ids = set(p['id'] for p in v1_results)
    v2_ids = set(p['id'] for p in v2_results)
    v3_ids = set(p['id'] for p in v3_results)

    all_ids = v1_ids | v2_ids | v3_ids
    in_all_three = v1_ids & v2_ids & v3_ids
    in_v3_only = v3_ids - v1_ids - v2_ids

    logger.info(f"   Total unique products: {len(all_ids)}")
    logger.info(f"   In all 3 methods: {len(in_all_three)}")
    logger.info(f"   Unique to V3: {len(in_v3_only)}")
    logger.info("=" * 80)

    return {
        'v1_results': v1_results,
        'v2_results': v2_results,
        'v3_results': v3_results,
        'distinctive_terms': distinctive_terms,
        'query': query,
        'stats': {
            'v1_count': len(v1_results),
            'v2_count': len(v2_results),
            'v3_count': len(v3_results),
            'distinctive_terms': distinctive_terms,
            'total_unique': len(all_ids),
            'in_all_three': len(in_all_three),
            'total_time': round(total_time, 2)
        }
    }
