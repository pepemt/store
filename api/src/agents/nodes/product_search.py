"""Product search node for querying the database"""
import logging
import asyncio
import sys
import os
import importlib.util

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _parent_dir)

from models import AgentState
from llm_config import llm
from metadata_cache import get_metadata_cache

# Import from tools.py (file) using importlib to avoid conflict with tools/ directory
_tools_py_path = os.path.join(_parent_dir, "tools.py")
_tools_spec = importlib.util.spec_from_file_location("tools_module", _tools_py_path)
_tools_module = importlib.util.module_from_spec(_tools_spec)
_tools_spec.loader.exec_module(_tools_module)
search_products_by_name = _tools_module.search_products_by_name
search_products_by_category = _tools_module.search_products_by_category
semantic_product_search = _tools_module.semantic_product_search
get_product_recommendations = _tools_module.get_product_recommendations

logger = logging.getLogger(__name__)


async def product_search_node(state: AgentState) -> dict:
    """
    Search for products based on user query.
    Uses LLM to extract search parameters and queries the database.
    """
    user_message = state["messages"][-1].content

    # Get metadata cache for context
    metadata_cache = get_metadata_cache()
    metadata_context = metadata_cache.get_formatted_context()

    # Use LLM to extract search parameters with database context
    extract_prompt = f"""Extract product search parameters from the user message. Use the available database values as reference.

{metadata_context}

IMPORTANT:
- Match the user's input to the closest available values above
- For colors, use exact matches from the Available Colors list
- For categories, map to Available Categories (e.g., "pantalón" → "Trousers", "camisa" → "Shirts")
- Be flexible with language (Spanish/English)

Return ONLY a JSON object with these fields (use null if not mentioned):
- search_query: string (general product name/keywords)
- category: string (exact match from Available Categories)
- color: string (exact match from Available Colors)
- product_group: string (from Available Product Groups, if specific)
- department: string (from Available Departments, if mentioned)

Examples:
Message: "Busco pantalón negro"
Response: {{"search_query": "pantalón", "category": "Trousers", "color": "Black", "product_group": "Garment Lower body", "department": null}}

Message: "Show me blue shirts"
Response: {{"search_query": "shirts", "category": "Shirts", "color": "Blue", "product_group": null, "department": null}}

Message: "I need black jackets"
Response: {{"search_query": "jackets", "category": "Jacket", "color": "Black", "product_group": null, "department": null}}

Now extract from:
Message: {user_message}
Response:"""

    try:
        # Extract parameters using LLM (async)
        extraction = await llm.ainvoke([{"role": "user", "content": extract_prompt}])
        logger.info(f"Extracted parameters: {extraction.content}")

        # Parse the extraction (simple parsing, could be improved with structured output)
        import json
        import re

        # Try to find JSON in response
        json_match = re.search(r'\{[^}]+\}', extraction.content)
        if json_match:
            params = json.loads(json_match.group())
        else:
            # Fallback: use the entire message as search query
            params = {"search_query": user_message, "category": None, "department": None}

        search_query = params.get("search_query")
        category = params.get("category")
        department = params.get("department")
        color = params.get("color")
        product_group = params.get("product_group")

        logger.info(f"Extracted filters - query: {search_query}, category: {category}, color: {color}, product_group: {product_group}, department: {department}")

        # Try search with all available filters
        products = []

        # Strategy 0: Try semantic search first (most flexible and intelligent)
        if search_query:
            try:
                logger.info("Attempting semantic search...")
                products = await semantic_product_search(query=user_message, limit=5)
                if products:
                    logger.info(f"Semantic search returned {len(products)} products")
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to literal search: {e}")

        # Strategy 1: Search with ALL filters if we have specific ones
        if not products and (category or color or product_group):
            products = await search_products_by_category(
                category=category,
                department=department,
                color=color,
                product_group=product_group,
                limit=5
            )
            logger.info(f"Search with all filters returned {len(products)} products")

        # Strategy 2: If no results, try with just name and color
        if not products and search_query and color:
            products = await search_products_by_name(
                query=search_query,
                color=color,
                limit=5
            )
            logger.info(f"Search with name+color returned {len(products)} products")

        # Strategy 3: If still no results, try with just name
        if not products and search_query:
            products = await search_products_by_name(query=search_query, limit=5)
            logger.info(f"Search with name only returned {len(products)} products")

        # Strategy 4: If still no products, try category without color
        if not products and category:
            products = await search_products_by_category(category=category, limit=5)
            logger.info(f"Search with category only returned {len(products)} products")

        # Strategy 5: Last resort - get general recommendations
        if not products:
            products = await get_product_recommendations(limit=5)
            logger.info(f"Fallback to recommendations returned {len(products)} products")

        # Format response with LLM
        if products:
            products_text = "\n".join([
                f"- {p['name']} (${p['price']:.2f}) - {p['category']} - {p['department']}"
                for p in products
            ])

            response_prompt = f"""You are a helpful shopping assistant. The user asked: "{user_message}"

I found these products:
{products_text}

Provide a friendly, helpful response presenting these products. Be concise but enthusiastic.
Mention key details like name, price, and category."""

            response = await llm.ainvoke([{"role": "user", "content": response_prompt}])
            response_content = response.content
        else:
            response_content = "Lo siento, no encontré productos que coincidan con tu búsqueda. ¿Podrías ser más específico o intentar con otros términos?"

        logger.info(f"Product search completed: {len(products)} products found")

        return {
            "messages": [{"role": "assistant", "content": response_content}],
            "products_found": products,
            "search_query": search_query,
            "category_filter": category,
            "department_filter": department,
            "next_action": "end"
        }

    except Exception as e:
        logger.error(f"Error in product search: {e}")
        error_response = "Disculpa, tuve un problema buscando productos. ¿Podrías intentar de nuevo?"
        return {
            "messages": [{"role": "assistant", "content": error_response}],
            "products_found": [],
            "next_action": "end"
        }
