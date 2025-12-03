"""
Generic unified search tool for the intelligent orchestrator.

This module provides a unified search interface that combines:
- Semantic search (V1, V2, V3)
- Review-based search
- Budget filtering
- Category filtering
"""

import logging
import sys
import os
import re
import json
import asyncio
import importlib.util
from typing import Optional, List, Dict, Any

# Add parent directory (agents) to path for imports
parent_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

from state import ProductDict, SearchResult, BudgetContext, AgentState
from llm_config import llm
from metadata_cache import get_metadata_cache
from progress_utils import emit_parallel_start, emit_parallel_end

# Import budget module directly using importlib to avoid circular import
budget_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "budget.py")
budget_spec = importlib.util.spec_from_file_location("budget_module", budget_py_path)
budget_module = importlib.util.module_from_spec(budget_spec)
budget_spec.loader.exec_module(budget_module)
filter_products_by_budget = budget_module.filter_products_by_budget

# Import from the original tools.py module (not the tools/ directory)
# We need to import it by its file path to avoid confusion with the directory
tools_py_path = os.path.join(parent_path, "tools.py")
spec = importlib.util.spec_from_file_location("tools_module", tools_py_path)
tools_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools_module)

# Extract the functions we need
semantic_product_search = tools_module.semantic_product_search
search_products_by_name = tools_module.search_products_by_name
search_products_by_category = tools_module.search_products_by_category
get_product_recommendations = tools_module.get_product_recommendations
_semantic_search_v1_terms = tools_module._semantic_search_v1_terms
_semantic_search_v2_full_query = tools_module._semantic_search_v2_full_query
_semantic_search_v3_distinctive = tools_module._semantic_search_v3_distinctive

logger = logging.getLogger(__name__)


# -----------------------------
# Query Refinement (LLM-based)
# -----------------------------

async def refine_search_query(
    original_query: str,
    image_description: Optional[str] = None,
    conversation_context: Optional[str] = None,
) -> str:
    """
    Refine and translate search query to English using LLM.

    This function:
    - Translates all terms to English
    - Normalizes product types with synonyms
    - Includes gender terms automatically
    - Matches terms to store inventory

    Args:
        original_query: The user's original query (any language)
        image_description: Optional image description for context
        conversation_context: Optional conversation history

    Returns:
        Refined query in English, space-separated terms
    """
    logger.info(f"Refining query: '{original_query}'")

    # Build search context
    search_context = f"User query: {original_query}"
    if image_description:
        search_context += f"\n\nImage description:\n{image_description}\n\nExtract product attributes from BOTH the text AND the image."
    if conversation_context:
        search_context = f"{conversation_context}\n\n{search_context}"

    # Get store context from metadata cache
    try:
        metadata_cache = get_metadata_cache()
        await metadata_cache.refresh()
        store_context = metadata_cache.get_formatted_context()
    except Exception as e:
        logger.warning(f"Failed to get store context: {e}")
        store_context = "Categories: Clothing, Shoes, Accessories\nDepartments: Men, Women, Kids"

    refinement_prompt = f"""You are a search query optimizer for a clothing store.

STORE INVENTORY (use these exact terms when possible):
{store_context}

USER QUERY:
{search_context}

TASK: Extract search terms as PLAIN TEXT separated by spaces, ALL IN ENGLISH.

CRITICAL RULES:
1. Output ONLY search terms separated by spaces (no JSON, no punctuation)
2. **TRANSLATE ALL TERMS TO ENGLISH** - Every single word must be in English
   - unicornio → unicorn
   - corazón → heart
   - estrella → star
   - flores → flowers
   - mariposa → butterfly
   - arcoíris → rainbow
   - pantalón/pantalones → trousers pants
   - playera/camiseta → t-shirt
   - vestido → dress
   - sudadera → hoodie sweatshirt
   - mezclilla/jean → jeans denim
3. For product types: include primary term + 1 synonym max (e.g., "trousers pants")
4. ALWAYS include gender terms: men, women, unisex, girls, boys, kids (NEVER omit these)
5. Match terms to our inventory categories when possible
6. Maximum 2 synonyms per concept

EXAMPLES:

Input: "Playera de unicornio para niña"
Output: t-shirt unicorn girls kids

Input: "Sudadera con corazones rosa"
Output: hoodie sweatshirt hearts pink

Input: "Recomiendame un pantalon negro para hombre"
Output: trousers pants jeans black men

Input: "Vestido con flores para mujer"
Output: dress flowers floral women

Input: "Camisa con estrellas azul"
Output: shirt stars blue

Now extract search terms (ALL IN ENGLISH, plain text only):"""

    try:
        response = await asyncio.wait_for(
            llm.ainvoke([{"role": "user", "content": refinement_prompt}]),
            timeout=30.0
        )
        refined_query = response.content.strip()
        logger.info(f"Query refined: '{original_query}' → '{refined_query}'")
        return refined_query
    except asyncio.TimeoutError:
        logger.warning("Query refinement timeout, using original")
        return original_query
    except Exception as e:
        logger.warning(f"Query refinement failed: {e}, using original")
        return original_query


# -----------------------------
# Product Discrimination (LLM-based)
# -----------------------------

async def discriminate_products(
    original_query: str,
    refined_query: str,
    v1_products: List[ProductDict],
    v2_products: List[ProductDict],
    v3_products: List[ProductDict],
    distinctive_terms: Optional[List[str]] = None,
    limit: int = 10,
) -> List[ProductDict]:
    """
    Use LLM to select the most relevant products from search results.

    This function:
    - Prioritizes V3 results (distinctive term matches)
    - Analyzes relevance by product name
    - Considers overlap between methods
    - Returns reordered top products

    Args:
        original_query: User's original query
        refined_query: Refined English query
        v1_products: Results from term-by-term search
        v2_products: Results from full query search
        v3_products: Results from distinctive terms search (PRIORITY!)
        distinctive_terms: List of distinctive terms used
        limit: Maximum products to return

    Returns:
        List of best products, ordered by relevance
    """
    all_products = v3_products + v1_products + v2_products

    if not all_products:
        logger.warning("No products to discriminate")
        return []

    # Build product dict for lookup
    all_products_dict = {p.get('id'): p for p in all_products if p.get('id')}

    # If we have few products, skip LLM discrimination
    if len(all_products_dict) <= limit:
        logger.info(f"Only {len(all_products_dict)} products, skipping discrimination")
        # Still prioritize V3
        return _fallback_prioritize(v1_products, v2_products, v3_products, limit)

    logger.info(f"Discriminating {len(all_products_dict)} products for query: '{original_query}'")

    def format_product_list(products: List[ProductDict], method_name: str) -> str:
        if not products:
            return f"No results from {method_name}"
        lines = []
        for p in products[:15]:  # Limit to avoid too long prompts
            matched = p.get('matched_terms', [])
            matched_str = f" | matched: {matched}" if matched else ""
            lines.append(
                f"  - ID:{p.get('id')} | {p.get('name', 'Unknown')} | {p.get('category', '')} | {p.get('color', '')} | ${p.get('price', 0):.2f}{matched_str}"
            )
        return "\n".join(lines)

    # Build distinctive terms section
    distinctive_section = ""
    if distinctive_terms:
        distinctive_section = f"""
## DISTINCTIVE TERMS (CRITICAL - MUST PRIORITIZE!)
The user is looking for: {', '.join(distinctive_terms)}
Products with these terms in their NAME are the MOST RELEVANT.
V3 products matched these terms directly - PRIORITIZE V3!
"""

    selector_prompt = f"""You are a product search quality controller. Select the TOP {limit} most relevant products.

## USER QUERY
"{original_query}"

## SEARCH TERMS
"{refined_query}"
{distinctive_section}
## SEARCH RESULTS (3 Methods)

### V3 - DISTINCTIVE MATCHES (HIGHEST PRIORITY!)
These products matched distinctive terms like "{distinctive_terms[0] if distinctive_terms else 'specific design'}" directly.
{format_product_list(v3_products, 'V3')}

### V1 - TERM-BY-TERM MATCHES
{format_product_list(v1_products, 'V1')}

### V2 - SEMANTIC MATCHES
{format_product_list(v2_products, 'V2')}

## SELECTION RULES (IN ORDER OF PRIORITY)

1. **V3 FIRST**: If V3 has products, they MUST be in top positions (they match distinctive terms).
2. **VERIFY BY NAME**: Look at product NAMES. If the distinctive term appears in the name, it's highly relevant.
3. **OVERLAP = CONFIDENCE**: Products appearing in multiple methods are reliable.
4. **USER INTENT**: Consider type (t-shirt, dress), color, gender from query.
5. **NO DUPLICATES**: Each ID appears only once.

## OUTPUT FORMAT
Return ONLY a JSON array of exactly {limit} product IDs, ordered by relevance:
[id1, id2, id3, ...]

Select the best products now:"""

    try:
        response = await asyncio.wait_for(
            llm.ainvoke([{"role": "user", "content": selector_prompt}]),
            timeout=15.0
        )

        response_text = response.content.strip()

        # Parse selected IDs
        json_match = re.search(r'\[[\d,\s]+\]', response_text)
        if json_match:
            selected_ids = json.loads(json_match.group())
        else:
            selected_ids = [int(x) for x in re.findall(r'\d+', response_text)][:limit]

        logger.info(f"LLM selected {len(selected_ids)} product IDs")

        # Build final list in LLM-selected order
        products = []
        seen_ids = set()
        for pid in selected_ids:
            if pid in all_products_dict and pid not in seen_ids:
                products.append(all_products_dict[pid])
                seen_ids.add(pid)

        # Fill remaining slots if needed
        if len(products) < limit:
            products = _fill_remaining(products, seen_ids, v1_products, v2_products, v3_products, limit)

        logger.info(f"Discrimination complete: {len(products)} final products")
        return products

    except Exception as e:
        logger.warning(f"LLM discrimination failed: {e}, using fallback")
        return _fallback_prioritize(v1_products, v2_products, v3_products, limit)


def _fallback_prioritize(
    v1_products: List[ProductDict],
    v2_products: List[ProductDict],
    v3_products: List[ProductDict],
    limit: int
) -> List[ProductDict]:
    """Fallback: prioritize V3 > V1 > V2 without LLM."""
    products = []
    seen_ids = set()

    # V3 first (distinctive matches)
    for p in v3_products:
        if len(products) >= limit:
            break
        pid = p.get('id')
        if pid and pid not in seen_ids:
            products.append(p)
            seen_ids.add(pid)

    # Then interleave V1 and V2
    for i in range(max(len(v1_products), len(v2_products))):
        if len(products) >= limit:
            break
        if i < len(v1_products):
            pid = v1_products[i].get('id')
            if pid and pid not in seen_ids:
                products.append(v1_products[i])
                seen_ids.add(pid)
        if len(products) >= limit:
            break
        if i < len(v2_products):
            pid = v2_products[i].get('id')
            if pid and pid not in seen_ids:
                products.append(v2_products[i])
                seen_ids.add(pid)

    return products


def _fill_remaining(
    products: List[ProductDict],
    seen_ids: set,
    v1_products: List[ProductDict],
    v2_products: List[ProductDict],
    v3_products: List[ProductDict],
    limit: int
) -> List[ProductDict]:
    """Fill remaining slots prioritizing V3 > V1 > V2."""
    for source in [v3_products, v1_products, v2_products]:
        for p in source:
            if len(products) >= limit:
                return products
            pid = p.get('id')
            if pid and pid not in seen_ids:
                products.append(p)
                seen_ids.add(pid)
    return products


class GenericSearchTool:
    """
    Unified search tool that combines all search strategies.

    The orchestrator decides which parameters to use, and this tool
    executes the appropriate searches and combines results.
    """

    def __init__(self):
        """Initialize the search tool."""
        self._review_engine = None

    async def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        budget_usd: Optional[float] = None,
        budget_context: Optional[BudgetContext] = None,
        search_reviews: bool = False,
        review_need: Optional[str] = None,
        limit: int = 10,
        strategies: Optional[List[str]] = None,
        include_recommendations: bool = False,
        customer_id: Optional[str] = None,
        image_description: Optional[str] = None,
        conversation_context: Optional[str] = None,
        skip_refinement: bool = False,
        skip_discrimination: bool = False,
        state: Optional[AgentState] = None,
    ) -> SearchResult:
        """
        Unified search interface with LLM refinement and discrimination.

        The orchestrator decides:
        - What query to use
        - What filters to apply
        - Whether to include review search
        - Budget constraints
        - Which strategies to use

        Args:
            query: Search query (text)
            filters: Optional filters (category, department, color, product_group)
            budget_usd: Budget in USD (simple float)
            budget_context: Full budget context with flexibility
            search_reviews: Whether to include review-based search
            review_need: Description of need for review search
            limit: Maximum results to return
            strategies: Search strategies to use ["v1", "v2", "v3", "hybrid", "keyword"]
            include_recommendations: Whether to include general recommendations
            customer_id: Customer ID for personalized recommendations
            image_description: Optional image description for context
            skip_refinement: Skip LLM query refinement (default: False)
            skip_discrimination: Skip LLM product discrimination (default: False)

        Returns:
            SearchResult with products and metadata
        """
        if strategies is None:
            strategies = ["v1", "v2", "v3"]

        logger.info(f"GenericSearchTool.search: query='{query}', strategies={strategies}")

        import time

        original_query = query
        all_products: List[ProductDict] = []
        strategies_used: List[str] = []

        # Track V1, V2, V3 results separately for discrimination
        v1_products: List[ProductDict] = []
        v2_products: List[ProductDict] = []
        v3_products: List[ProductDict] = []
        distinctive_terms: List[str] = []

        # Timing metrics
        refine_time_ms = 0
        search_time_ms = 0
        discrimination_time_ms = 0

        # 0. Refine query with LLM (translate to English, normalize)
        refined_query = query
        if query and not skip_refinement:
            try:
                refine_start = time.time()
                refined_query = await refine_search_query(
                    original_query=query,
                    image_description=image_description,
                    conversation_context=conversation_context
                )
                refine_time_ms = int((time.time() - refine_start) * 1000)
                strategies_used.append("refinement")
                logger.info(f"  Query refined: '{query}' → '{refined_query}' ({refine_time_ms}ms)")
            except Exception as e:
                logger.warning(f"Query refinement failed: {e}, using original")
                refined_query = query

        # 1. Semantic search (V1, V2, V3 or hybrid)
        if refined_query and any(s in strategies for s in ["v1", "v2", "v3", "hybrid"]):
            # Emit parallel start event (like the original system)
            if state:
                await emit_parallel_start(
                    state=state,
                    parallel_group="search_hybrid",
                    title="Búsqueda híbrida",
                    description="Ejecutando 3 estrategias de búsqueda en paralelo...",
                    steps=["V1: Término por término", "V2: Query completa", "V3: Términos distintivos"]
                )

            search_start = time.time()
            v1_products, v2_products, v3_products, distinctive_terms = await self._run_semantic_search_detailed(
                refined_query, strategies, max(limit * 3, 30)  # Get many candidates for discrimination
            )
            search_time_ms = int((time.time() - search_start) * 1000)

            # Emit parallel end event
            if state:
                await emit_parallel_end(
                    state=state,
                    parallel_group="search_hybrid",
                    title="Búsqueda completada",
                    description=f"V1: {len(v1_products)}, V2: {len(v2_products)}, V3: {len(v3_products)} productos",
                    duration_ms=search_time_ms
                )

            all_products = v3_products + v1_products + v2_products
            strategies_used.append("semantic")
            logger.info(f"  Semantic search returned {len(all_products)} products (V1:{len(v1_products)}, V2:{len(v2_products)}, V3:{len(v3_products)}) in {search_time_ms}ms")

        # 2. Keyword search (fallback or explicit)
        if query and "keyword" in strategies:
            keyword_results = await self._run_keyword_search(query, filters, limit)
            all_products.extend(keyword_results)
            strategies_used.append("keyword")
            logger.info(f"  Keyword search returned {len(keyword_results)} products")

        # 3. Category/filter search
        if filters and not query:
            filter_results = await self._run_filter_search(filters, limit)
            all_products.extend(filter_results)
            strategies_used.append("filters")
            logger.info(f"  Filter search returned {len(filter_results)} products")

        # 4. Review-based search
        if search_reviews and review_need:
            review_results = await self._run_review_search(review_need, limit)
            all_products.extend(review_results)
            strategies_used.append("reviews")
            logger.info(f"  Review search returned {len(review_results)} products")

        # 5. Recommendations (if requested or as fallback)
        if include_recommendations or (not all_products and not query):
            rec_results = await get_product_recommendations(customer_id, limit)
            all_products.extend(rec_results)
            strategies_used.append("recommendations")
            logger.info(f"  Recommendations returned {len(rec_results)} products")

        # 6. Deduplicate by product ID
        seen_ids = set()
        unique_products = []
        for p in all_products:
            pid = p.get("id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_products.append(p)

        logger.info(f"  After deduplication: {len(unique_products)} unique products")

        # 7. Discriminate with LLM FIRST (prioritize V3 distinctive terms)
        # This happens BEFORE budget/additional filters to ensure V3 gets priority
        if not skip_discrimination and (v1_products or v2_products or v3_products):
            try:
                discrimination_start = time.time()
                # Use full V1, V2, V3 results (not filtered)
                discriminated_products = await discriminate_products(
                    original_query=original_query or "",
                    refined_query=refined_query or "",
                    v1_products=v1_products,
                    v2_products=v2_products,
                    v3_products=v3_products,
                    distinctive_terms=distinctive_terms,
                    limit=max(limit * 2, 20)  # Get more, filter later
                )
                discrimination_time_ms = int((time.time() - discrimination_start) * 1000)
                strategies_used.append("discrimination")
                logger.info(f"  After discrimination: {len(discriminated_products)} products (V3 prioritized) in {discrimination_time_ms}ms")
                logger.info(f"  Distinctive terms: {distinctive_terms}")
            except Exception as e:
                logger.warning(f"Discrimination failed: {e}, using fallback V3>V1>V2")
                discriminated_products = unique_products
        else:
            discriminated_products = unique_products

        # 8. Apply budget filter (AFTER discrimination)
        if budget_context:
            discriminated_products = filter_products_by_budget(
                discriminated_products,
                budget_context,
                num_items=1
            )
            strategies_used.append("budget_filter")
            logger.info(f"  After budget filter: {len(discriminated_products)} products")
        elif budget_usd:
            max_price = budget_usd * 1.1
            discriminated_products = [p for p in discriminated_products if p.get("price", float("inf")) <= max_price]
            strategies_used.append("budget_filter")
            logger.info(f"  After budget filter (${budget_usd}): {len(discriminated_products)} products")

        # 9. Apply additional filters (AFTER discrimination)
        if filters:
            discriminated_products = self._apply_filters(discriminated_products, filters)
            logger.info(f"  After additional filters: {len(discriminated_products)} products")

        # 10. Final limit
        final_products = discriminated_products[:limit]

        logger.info(f"  Final result: {len(final_products)} products")
        if v1_products or v2_products or v3_products:
            # Count how many came from each source
            final_ids = {p.get('id') for p in final_products}
            v1_in_final = sum(1 for p in v1_products if p.get('id') in final_ids)
            v2_in_final = sum(1 for p in v2_products if p.get('id') in final_ids)
            v3_in_final = sum(1 for p in v3_products if p.get('id') in final_ids)
            logger.info(f"  V1 contributed: {v1_in_final}")
            logger.info(f"  V2 contributed: {v2_in_final}")
            logger.info(f"  V3 contributed: {v3_in_final} ← DISTINCTIVE")

        # Compute contribution counts
        final_ids = {p.get('id') for p in final_products}
        v1_final = sum(1 for p in v1_products if p.get('id') in final_ids) if v1_products else 0
        v2_final = sum(1 for p in v2_products if p.get('id') in final_ids) if v2_products else 0
        v3_final = sum(1 for p in v3_products if p.get('id') in final_ids) if v3_products else 0

        # Determine search method
        search_method = "hybrid" if ("semantic" in strategies_used) else "keyword"
        if not strategies_used:
            search_method = "none"

        return SearchResult(
            products=final_products,
            strategies_used=strategies_used,
            search_method=search_method,
            budget_applied=budget_usd or (budget_context.amount_usd if budget_context else None),
            total_found=len(unique_products),
            v1_count=v1_final,
            v2_count=v2_final,
            v3_count=v3_final,
            distinctive_terms=distinctive_terms if distinctive_terms else [],
            refine_time_ms=refine_time_ms,
            search_time_ms=search_time_ms,
            discrimination_time_ms=discrimination_time_ms,
        )

    async def _run_semantic_search(
        self,
        query: str,
        strategies: List[str],
        limit: int
    ) -> List[ProductDict]:
        """Run semantic search with specified strategies."""
        all_results = []

        # Use hybrid search if all strategies requested
        if set(strategies) >= {"v1", "v2", "v3"} or "hybrid" in strategies:
            try:
                hybrid_result = await semantic_product_search(query, limit)
                # Combine V1, V2, V3 results
                all_results.extend(hybrid_result.get('v1_results', []))
                all_results.extend(hybrid_result.get('v2_results', []))
                all_results.extend(hybrid_result.get('v3_results', []))
            except Exception as e:
                logger.error(f"Hybrid search failed: {e}")
        else:
            # Run individual strategies
            if "v1" in strategies:
                try:
                    v1_results = await _semantic_search_v1_terms(query, limit)
                    all_results.extend(v1_results)
                except Exception as e:
                    logger.error(f"V1 search failed: {e}")

            if "v2" in strategies:
                try:
                    v2_results = await _semantic_search_v2_full_query(query, limit)
                    all_results.extend(v2_results)
                except Exception as e:
                    logger.error(f"V2 search failed: {e}")

            if "v3" in strategies:
                try:
                    v3_results, _ = await _semantic_search_v3_distinctive(query, limit)
                    all_results.extend(v3_results)
                except Exception as e:
                    logger.error(f"V3 search failed: {e}")

        return all_results

    async def _run_semantic_search_detailed(
        self,
        query: str,
        strategies: List[str],
        limit: int
    ) -> tuple[List[ProductDict], List[ProductDict], List[ProductDict], List[str]]:
        """
        Run semantic search and return V1, V2, V3 results separately.

        Returns:
            Tuple of (v1_products, v2_products, v3_products, distinctive_terms)
        """
        v1_products: List[ProductDict] = []
        v2_products: List[ProductDict] = []
        v3_products: List[ProductDict] = []
        distinctive_terms: List[str] = []

        # Use hybrid search if all strategies requested
        if set(strategies) >= {"v1", "v2", "v3"} or "hybrid" in strategies:
            try:
                hybrid_result = await semantic_product_search(query, limit)
                v1_products = hybrid_result.get('v1_results', [])
                v2_products = hybrid_result.get('v2_results', [])
                v3_products = hybrid_result.get('v3_results', [])
                distinctive_terms = hybrid_result.get('distinctive_terms', [])
            except Exception as e:
                logger.error(f"Hybrid search failed: {e}")
        else:
            # Run individual strategies
            if "v1" in strategies:
                try:
                    v1_products = await _semantic_search_v1_terms(query, limit)
                except Exception as e:
                    logger.error(f"V1 search failed: {e}")

            if "v2" in strategies:
                try:
                    v2_products = await _semantic_search_v2_full_query(query, limit)
                except Exception as e:
                    logger.error(f"V2 search failed: {e}")

            if "v3" in strategies:
                try:
                    v3_products, distinctive_terms = await _semantic_search_v3_distinctive(query, limit)
                except Exception as e:
                    logger.error(f"V3 search failed: {e}")

        return v1_products, v2_products, v3_products, distinctive_terms

    async def _run_keyword_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> List[ProductDict]:
        """Run keyword-based search."""
        try:
            color = filters.get("color") if filters else None
            product_group = filters.get("product_group") if filters else None

            results = await search_products_by_name(
                query=query,
                color=color,
                product_group=product_group,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    async def _run_filter_search(
        self,
        filters: Dict[str, Any],
        limit: int
    ) -> List[ProductDict]:
        """Run filter-based search (no query)."""
        try:
            results = await search_products_by_category(
                category=filters.get("category"),
                department=filters.get("department"),
                color=filters.get("color"),
                product_group=filters.get("product_group"),
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Filter search failed: {e}")
            return []

    async def _run_review_search(
        self,
        review_need: str,
        limit: int
    ) -> List[ProductDict]:
        """Run review-based search."""
        try:
            # Lazy import to avoid circular dependencies
            if self._review_engine is None:
                try:
                    from review_search import ReviewSearchEngine
                    self._review_engine = ReviewSearchEngine()
                except ImportError:
                    logger.warning("ReviewSearchEngine not available")
                    return []

            review_results = self._review_engine.search_reviews(review_need, top_k=50)
            aggregated = self._review_engine.aggregate_products(review_results, top_n=limit)
            products = self._review_engine.get_products(aggregated)

            return products

        except Exception as e:
            logger.error(f"Review search failed: {e}")
            return []

    # Category synonyms for flexible matching
    CATEGORY_SYNONYMS = {
        "jeans": ["trousers", "pants", "denim", "jeans"],
        "pants": ["trousers", "pants", "jeans"],
        "trousers": ["trousers", "pants", "jeans"],
        "shirt": ["shirt", "blouse", "top"],
        "tshirt": ["t-shirt", "tee", "top", "jersey"],
        "t-shirt": ["t-shirt", "tee", "top", "jersey"],
        "dress": ["dress", "gown"],
        "jacket": ["jacket", "coat", "blazer", "outerwear"],
        "shoes": ["shoes", "footwear", "sneakers", "boots"],
    }

    # Gender to department mapping
    GENDER_DEPARTMENT_MAP = {
        "male": ["men", "menswear", "man", "divided"],
        "men": ["men", "menswear", "man", "divided"],
        "female": ["women", "ladies", "woman", "divided"],
        "women": ["women", "ladies", "woman", "divided"],
        "kids": ["kids", "children", "baby", "boys", "girls"],
        "boys": ["boys", "kids", "children"],
        "girls": ["girls", "kids", "children"],
    }

    def _apply_filters(
        self,
        products: List[ProductDict],
        filters: Dict[str, Any]
    ) -> List[ProductDict]:
        """
        Apply additional filters to product list with graceful fallback.

        If a filter would eliminate all products, skip it.
        This ensures we always return results from semantic search.
        """
        if not filters or not products:
            return products

        # Validate filters is a dict, not a string
        if isinstance(filters, str):
            logger.warning(f"Filters is a string, not a dict: '{filters[:100]}'. Skipping filters.")
            return products

        filtered = products
        original_count = len(products)

        # Apply gender filter (maps to department)
        if "gender" in filters and filters["gender"]:
            gender = filters["gender"].lower()
            dept_terms = self.GENDER_DEPARTMENT_MAP.get(gender, [gender])

            gender_filtered = [
                p for p in filtered
                if any(
                    term in (p.get("department", "") or "").lower()
                    or term in (p.get("index_group_name", "") or "").lower()
                    for term in dept_terms
                )
            ]
            # Only apply if we still have results
            if gender_filtered:
                filtered = gender_filtered
                logger.info(f"  Gender filter '{gender}': {len(filtered)} products remain")
            else:
                logger.info(f"  Gender filter '{gender}' skipped (would eliminate all)")

        # Apply category filter with synonyms
        if "category" in filters and filters["category"]:
            cat = filters["category"].lower()
            cat_terms = self.CATEGORY_SYNONYMS.get(cat, [cat])

            cat_filtered = [
                p for p in filtered
                if any(
                    term in (p.get("category", "") or "").lower()
                    or term in (p.get("product_type", "") or "").lower()
                    or term in (p.get("product_group", "") or "").lower()
                    for term in cat_terms
                )
            ]
            if cat_filtered:
                filtered = cat_filtered
                logger.info(f"  Category filter '{cat}': {len(filtered)} products remain")
            else:
                logger.info(f"  Category filter '{cat}' skipped (would eliminate all)")

        # Apply department filter
        if "department" in filters and filters["department"]:
            dept = filters["department"].lower()
            dept_filtered = [
                p for p in filtered
                if dept in (p.get("department", "") or "").lower()
            ]
            if dept_filtered:
                filtered = dept_filtered
                logger.info(f"  Department filter '{dept}': {len(filtered)} products remain")
            else:
                logger.info(f"  Department filter '{dept}' skipped (would eliminate all)")

        # Apply color filter
        if "color" in filters and filters["color"]:
            color = filters["color"].lower()
            color_filtered = [
                p for p in filtered
                if color in (p.get("color", "") or "").lower()
                or color in (p.get("color_group", "") or "").lower()
            ]
            if color_filtered:
                filtered = color_filtered
                logger.info(f"  Color filter '{color}': {len(filtered)} products remain")
            else:
                logger.info(f"  Color filter '{color}' skipped (would eliminate all)")

        # Apply product_group filter
        if "product_group" in filters and filters["product_group"]:
            pg = filters["product_group"].lower()
            pg_filtered = [
                p for p in filtered
                if pg in (p.get("product_group", "") or "").lower()
            ]
            if pg_filtered:
                filtered = pg_filtered
                logger.info(f"  Product group filter '{pg}': {len(filtered)} products remain")
            else:
                logger.info(f"  Product group filter '{pg}' skipped (would eliminate all)")

        logger.info(f"  Filters applied: {original_count} -> {len(filtered)} products")
        return filtered


# -----------------------------
# Convenience Functions
# -----------------------------

# Global search tool instance
_search_tool = GenericSearchTool()


async def search_products(
    query: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    budget_usd: Optional[float] = None,
    budget_context: Optional[BudgetContext] = None,
    search_reviews: bool = False,
    review_need: Optional[str] = None,
    limit: int = 10,
    strategies: Optional[List[str]] = None,
    include_recommendations: bool = False,
    customer_id: Optional[str] = None,
    image_description: Optional[str] = None,
    conversation_context: Optional[str] = None,
    skip_refinement: bool = False,
    skip_discrimination: bool = False,
    state: Optional[AgentState] = None,
) -> SearchResult:
    """
    Search products using the global search tool.

    This is the main entry point for the orchestrator to search products.
    Includes LLM-based query refinement (translation to English) and
    product discrimination (intelligent selection).

    Args:
        state: Optional agent state for emitting progress events
    """
    return await _search_tool.search(
        query=query,
        filters=filters,
        budget_usd=budget_usd,
        budget_context=budget_context,
        search_reviews=search_reviews,
        review_need=review_need,
        limit=limit,
        strategies=strategies,
        include_recommendations=include_recommendations,
        customer_id=customer_id,
        image_description=image_description,
        conversation_context=conversation_context,
        skip_refinement=skip_refinement,
        skip_discrimination=skip_discrimination,
        state=state,
    )
