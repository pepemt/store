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
    import time
    start_time = time.time()

    user_message = state["messages"][-1].content
    logger.info("=" * 80)
    logger.info(f"🔍 SEMANTIC SEARCH NODE START: '{user_message}'")
    logger.info("=" * 80)

    try:
        # Step 1: Extract key product attributes from user query
        refinement_prompt = f"""Extract ONLY the product search attributes from this user query. Ignore context, intentions, and extra information.

User query: {user_message}

Extract:
- Product type (e.g., "sandals", "necklace", "shirt")
- Color (if mentioned)
- Gender (if mentioned: "men", "women", "unisex")
- Key characteristics (e.g., "leather", "cotton", "casual")

Return ONLY the essential search terms separated by spaces, in English.
Focus on what the product IS, not what it's FOR or how it will be used.

Examples:
Input: "Recomiéndame collares bonitos"
Output: necklace

Input: "Sandalias para andar en mi casa para descansar de hombre negras"
Output: sandals men black

Input: "Quiero una camisa azul de algodón"
Output: shirt blue cotton

Now extract from: {user_message}
Search terms:"""

        logger.info("⏱️  Step 1: Calling LLM to refine query...")
        llm_start = time.time()
        try:
            import asyncio
            # Apply 30 second timeout to LLM call
            refinement_response = await asyncio.wait_for(
                llm.ainvoke([{"role": "user", "content": refinement_prompt}]),
                timeout=30.0
            )
            refined_query = refinement_response.content.strip()
            llm_time = time.time() - llm_start
            logger.info(f"✅ Query refined successfully in {llm_time:.2f}s")
            logger.info(f"   Original query: {user_message}")
            logger.info(f"   Refined search terms: {refined_query}")
        except asyncio.TimeoutError:
            llm_time = time.time() - llm_start
            logger.error(f"❌ LLM refinement timeout after {llm_time:.2f}s")
            # Fallback: use original query if refinement times out
            refined_query = user_message
            logger.info(f"   Fallback: using original query '{refined_query}'")
        except Exception as llm_error:
            llm_time = time.time() - llm_start
            logger.error(f"❌ LLM refinement failed after {llm_time:.2f}s: {llm_error}")
            # Fallback: use original query if refinement fails
            refined_query = user_message
            logger.info(f"   Fallback: using original query '{refined_query}'")

        # Step 2: Use semantic search with refined query
        logger.info(f"⏱️  Step 2: Calling semantic_product_search with refined query...")
        search_start = time.time()
        products = await semantic_product_search(query=refined_query, limit=10)
        search_time = time.time() - search_start

        if products:
            logger.info(f"✅ Semantic search found {len(products)} products in {search_time:.2f}s")

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

        total_time = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"✅ SEMANTIC SEARCH NODE COMPLETE in {total_time:.2f}s")
        logger.info(f"   Products found: {len(products)}")
        logger.info("=" * 80)

        return {
            "messages": [{"role": "assistant", "content": response_content}],
            "products_found": products,
            "search_method": "semantic",
            "next_action": "end"
        }

    except Exception as e:
        total_time = time.time() - start_time
        logger.error("=" * 80)
        logger.error(f"❌ ERROR in semantic product search after {total_time:.2f}s")
        logger.error(f"   Error: {e}", exc_info=True)
        logger.error("=" * 80)
        error_response = "Disculpa, tuve un problema con la búsqueda semántica. ¿Podrías intentar de nuevo?"
        return {
            "messages": [{"role": "assistant", "content": error_response}],
            "products_found": [],
            "next_action": "end"
        }
