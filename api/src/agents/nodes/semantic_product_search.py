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

    messages = state["messages"]
    user_message = messages[-1].content if messages else ""

    # Get image description from current state or conversation context
    image_description = state.get("image_description")
    conversation_context = state.get("conversation_context", {})

    # If no current image description, check context for recent one
    if not image_description and conversation_context.get("last_image_description"):
        image_description = conversation_context.get("last_image_description")
        logger.info("Semantic search: using image description from conversation context")

    # Build conversation history for context (last 4 messages for search relevance)
    history_context = ""
    if len(messages) > 1:
        recent_messages = messages[-5:-1]  # Get up to 4 previous messages
        history_lines = []
        for msg in recent_messages:
            role = getattr(msg, 'role', 'unknown') if hasattr(msg, 'role') else (
                msg.get('role', 'unknown') if isinstance(msg, dict) else 'unknown'
            )
            content = getattr(msg, 'content', str(msg)) if hasattr(msg, 'content') else (
                msg.get('content', str(msg)) if isinstance(msg, dict) else str(msg)
            )
            content_preview = content[:300] + "..." if len(content) > 300 else content
            history_lines.append(f"  {role}: {content_preview}")
        if history_lines:
            history_context = "Recent conversation:\n" + "\n".join(history_lines) + "\n\n"

    logger.info("=" * 80)
    logger.info(f"🔍 SEMANTIC SEARCH NODE START: '{user_message}'")
    if image_description:
        logger.info(f"   📷 Image description available: '{image_description[:100]}...'")
    if history_context:
        logger.info(f"   📜 Using {len(messages)-1} messages from conversation history")
    logger.info("=" * 80)

    try:
        # Build search context - include image description and history if available
        if image_description:
            search_context = f"""{history_context}User query: {user_message}

Image description (from current or recent message):
{image_description}

Extract the product attributes from BOTH the user's text AND the image description.
If the user refers to "esto", "algo así", "similar", they mean the image above."""
        elif history_context:
            search_context = f"""{history_context}User query: {user_message}

Consider the conversation context when extracting search terms."""
        else:
            search_context = f"User query: {user_message}"

        # Step 1: Extract key product attributes from user query
        refinement_prompt = f"""Extract ONLY the product search attributes from this query. Ignore context, intentions, and extra information.

{search_context}

Extract:
- Product type (e.g., "skirt", "sandals", "necklace", "shirt", "dress")
- Color (if mentioned)
- Gender (if mentioned: "men", "women", "unisex")
- Key characteristics (e.g., "short", "pleated", "leather", "cotton", "casual", "elegant")

Return ONLY the essential search terms separated by spaces, in English.
Focus on what the product IS, not what it's FOR or how it will be used.

Examples:
Input: "Recomiéndame collares bonitos"
Output: necklace

Input: "Sandalias para andar en mi casa para descansar de hombre negras"
Output: sandals men black

Input: Image shows "falda corta negra con pliegues"
Output: skirt black short pleated

Input: "Quiero algo como esto" + Image shows "vestido rojo elegante"
Output: dress red elegant

Now extract the search terms:"""

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

            # Build response context - include image description if available
            image_context = ""
            if image_description:
                image_context = f"""
The user also sent an image. You analyzed it and saw: {image_description[:300]}
Based on this image, you searched for similar products."""

            response_prompt = f"""You are a helpful shopping assistant. The user asked: "{user_message}"
{image_context}

I found these products using semantic search (ranked by relevance):
{products_text}

IMPORTANT: Respond in the SAME LANGUAGE as the user's query.
- If the user wrote in Spanish, respond in Spanish
- If the user wrote in English, respond in English
- If the user sent an image, acknowledge that you saw and understood what was in it

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
