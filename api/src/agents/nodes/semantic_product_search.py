"""Semantic product search node using vector similarity"""
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import AgentState
from llm_config import llm
from tools import semantic_product_search

logger = logging.getLogger(__name__)


async def semantic_product_search_node(state: AgentState) -> dict:
    """
    Search for products using semantic similarity.
    Uses vector embeddings to find products based on meaning, not just keywords.
    """
    user_message = state["messages"][-1].content
    logger.info(f"Semantic search for: {user_message}")

    try:
        # Step 1: Translate query to English for search (if needed)
        translation_prompt = f"""Translate the following product search query to English.
If it's already in English, return it as-is.
Only return the translated query, nothing else.

Query: {user_message}
Translated query:"""

        translation_response = await llm.ainvoke([{"role": "user", "content": translation_prompt}])
        english_query = translation_response.content.strip()

        logger.info(f"Original query: {user_message}")
        logger.info(f"English query for search: {english_query}")

        # Step 2: Use semantic search with English query
        products = await semantic_product_search(query=english_query, limit=10)

        if products:
            logger.info(f"Semantic search found {len(products)} products")

            # Format response with LLM
            products_text = "\n".join([
                f"- {p['name']} (${p['price']:.2f}) - {p['category']} - {p['color']} - Relevance: {p.get('relevance_score', 'N/A')}"
                for p in products
            ])

            response_prompt = f"""You are a helpful shopping assistant. The user asked: "{user_message}"

I found these products using semantic search (ranked by relevance):
{products_text}

IMPORTANT: Respond in the SAME LANGUAGE as the user's query.
- If the user wrote in Spanish, respond in Spanish
- If the user wrote in English, respond in English

Provide a friendly, helpful response presenting these products. Be concise but enthusiastic.
Mention key details like name, price, category, and color."""

            response = await llm.ainvoke([{"role": "user", "content": response_prompt}])
            response_content = response.content
        else:
            logger.warning("Semantic search returned no products")

            # Detect language for error message
            error_prompt = f"""The user asked: "{user_message}"

No products were found. Provide a polite apology in the SAME LANGUAGE as the user's query.
Keep it brief and suggest they try different terms."""

            error_response = await llm.ainvoke([{"role": "user", "content": error_prompt}])
            response_content = error_response.content

        logger.info(f"Semantic search completed: {len(products)} products found")

        return {
            "messages": [{"role": "assistant", "content": response_content}],
            "products_found": products,
            "search_method": "semantic",
            "next_action": "end"
        }

    except Exception as e:
        logger.error(f"Error in semantic product search: {e}")
        error_response = "Disculpa, tuve un problema con la búsqueda semántica. ¿Podrías intentar de nuevo?"
        return {
            "messages": [{"role": "assistant", "content": error_response}],
            "products_found": [],
            "next_action": "end"
        }
