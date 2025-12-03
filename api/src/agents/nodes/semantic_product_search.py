"""Semantic product search node using vector similarity"""
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import AgentState, StepType, StepStatus
from llm_config import llm
from tools import semantic_product_search
from metadata_cache import get_metadata_cache
from progress_utils import emit_progress, emit_parallel_start, emit_parallel_end

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

        # Step 1: Get store context from metadata cache
        metadata_cache = get_metadata_cache()
        await metadata_cache.refresh()
        store_context = metadata_cache.get_formatted_context()

        # Step 2: Extract key product attributes from user query with store context
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
3. For product types: include primary term + 1 synonym max (e.g., "trousers pants")
4. ALWAYS include gender terms: men, women, unisex, girls, boys (NEVER omit these)
5. Match terms to our inventory categories when possible
6. Maximum 2 synonyms per concept

EXAMPLES:

Input: "Playera de unicornio para niña"
Output: t-shirt unicorn girls

Input: "Sudadera con corazones rosa"
Output: hoodie sweatshirt hearts pink

Input: "Recomiendame un pantalon negro para hombre"
Output: trousers pants black men

Input: "Vestido con flores para mujer"
Output: dress flowers floral women

Input: "Camisa con estrellas azul"
Output: shirt stars blue

Now extract search terms (ALL IN ENGLISH, plain text only):"""

        # Emitir evento de refinamiento de query
        await emit_progress(
            state=state,
            step_type=StepType.SEARCH_REFINE,
            status=StepStatus.STARTED,
            title="Refinando búsqueda",
            description="Extrayendo términos clave con IA...",
            details={"original_query": user_message[:50]}
        )

        logger.info("⏱️  Step 2: Calling LLM to refine query...")
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

            # Emitir evento de refinamiento completado
            await emit_progress(
                state=state,
                step_type=StepType.SEARCH_REFINE,
                status=StepStatus.COMPLETED,
                title="Query refinada",
                description=f"Términos: {refined_query[:60]}...",
                details={"refined_query": refined_query},
                duration_ms=int(llm_time * 1000)
            )
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

        # Step 3: Execute HYBRID search (V1 + V2 + V3 in parallel)
        # Emitir evento de inicio de búsqueda paralela
        await emit_parallel_start(
            state=state,
            parallel_group="search_hybrid",
            title="Búsqueda híbrida",
            description="Ejecutando 3 estrategias de búsqueda en paralelo...",
            steps=["V1: Término por término", "V2: Query completa", "V3: Términos distintivos"]
        )

        logger.info(f"⏱️  Step 3: Calling HYBRID semantic_product_search (V1+V2+V3)...")
        search_start = time.time()
        search_results = await semantic_product_search(query=refined_query, limit=10)
        search_time = time.time() - search_start

        v1_products = search_results.get('v1_results', [])
        v2_products = search_results.get('v2_results', [])
        v3_products = search_results.get('v3_results', [])
        distinctive_terms = search_results.get('distinctive_terms', [])
        stats = search_results.get('stats', {})

        logger.info(f"✅ Hybrid search completed in {search_time:.2f}s")
        logger.info(f"   V1 (term-by-term): {len(v1_products)} products")
        logger.info(f"   V2 (full query):   {len(v2_products)} products")
        logger.info(f"   V3 (distinctive):  {len(v3_products)} products ← PRIORITY")
        if distinctive_terms:
            logger.info(f"   Distinctive terms: {distinctive_terms}")

        # Emitir evento de búsqueda paralela completada
        await emit_parallel_end(
            state=state,
            parallel_group="search_hybrid",
            title="Búsqueda completada",
            description=f"V1: {len(v1_products)}, V2: {len(v2_products)}, V3: {len(v3_products)} productos",
            duration_ms=int(search_time * 1000)
        )

        # Combine results - use all three sets
        all_products = v3_products + v1_products + v2_products  # V3 first for priority

        if all_products:
            # Step 4: LLM DISCRIMINATOR selects the best products
            logger.info("⏱️  Step 4: LLM DISCRIMINATOR selecting best products...")

            # Emitir evento de discriminador
            await emit_progress(
                state=state,
                step_type=StepType.DISCRIMINATOR,
                status=StepStatus.STARTED,
                title="Seleccionando mejores",
                description="Analizando relevancia de productos encontrados...",
                details={"total_candidates": len(all_products)}
            )

            def format_product_list(products, method_name):
                if not products:
                    return f"No results from {method_name}"
                lines = []
                for p in products:
                    matched = p.get('matched_terms', [])
                    matched_str = f" | matched: {matched}" if matched else ""
                    lines.append(
                        f"  - ID:{p['id']} | {p['name']} | {p['category']} | {p['color']} | ${p['price']:.2f}{matched_str}"
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

            selector_prompt = f"""You are a product search quality controller. Select the TOP 10 most relevant products.

## USER QUERY
"{user_message}"

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
2. **VERIFY BY NAME**: Look at product NAMES. If "{distinctive_terms[0] if distinctive_terms else 'the design'}" appears in the name, it's highly relevant.
3. **OVERLAP = CONFIDENCE**: Products appearing in multiple methods are reliable.
4. **USER INTENT**: Consider type (t-shirt, dress), color, gender from query.
5. **NO DUPLICATES**: Each ID appears only once.

## OUTPUT FORMAT
Return ONLY a JSON array of exactly 10 product IDs, ordered by relevance:
[id1, id2, id3, id4, id5, id6, id7, id8, id9, id10]

Select the best products now:"""

            try:
                import json as json_module
                import re
                selector_response = await asyncio.wait_for(
                    llm.ainvoke([{"role": "user", "content": selector_prompt}]),
                    timeout=15.0
                )

                # Parse selected IDs from LLM response
                response_text = selector_response.content.strip()
                json_match = re.search(r'\[[\d,\s]+\]', response_text)
                if json_match:
                    selected_ids = json_module.loads(json_match.group())
                else:
                    selected_ids = [int(x) for x in re.findall(r'\d+', response_text)][:10]

                logger.info(f"   LLM selected {len(selected_ids)} product IDs: {selected_ids[:5]}...")

                # Build final product list in LLM-selected order
                all_products_dict = {p['id']: p for p in all_products}
                products = []
                seen_ids = set()
                for pid in selected_ids:
                    if pid in all_products_dict and pid not in seen_ids:
                        products.append(all_products_dict[pid])
                        seen_ids.add(pid)

                # If LLM didn't select enough, fill with V3 first, then V1, then V2
                if len(products) < 10:
                    # Priority: V3 > V1 > V2
                    for source in [v3_products, v1_products, v2_products]:
                        for p in source:
                            if len(products) >= 10:
                                break
                            if p['id'] not in seen_ids:
                                products.append(p)
                                seen_ids.add(p['id'])

                logger.info(f"   Final selection: {len(products)} products")

                # Emitir evento de discriminador completado
                await emit_progress(
                    state=state,
                    step_type=StepType.DISCRIMINATOR,
                    status=StepStatus.COMPLETED,
                    title="Productos seleccionados",
                    description=f"Top {len(products)} productos más relevantes",
                    details={"selected_count": len(products)}
                )

            except Exception as selector_error:
                logger.warning(f"LLM discriminator failed: {selector_error}, using fallback")
                # Fallback: V3 first (distinctive), then interleave V1 and V2
                products = []
                seen_ids = set()

                # Add all V3 products first (they match distinctive terms)
                for p in v3_products:
                    if len(products) >= 10:
                        break
                    if p['id'] not in seen_ids:
                        products.append(p)
                        seen_ids.add(p['id'])

                # Then interleave V1 and V2
                for i in range(max(len(v1_products), len(v2_products))):
                    if len(products) >= 10:
                        break
                    if i < len(v1_products) and v1_products[i]['id'] not in seen_ids:
                        products.append(v1_products[i])
                        seen_ids.add(v1_products[i]['id'])
                    if len(products) >= 10:
                        break
                    if i < len(v2_products) and v2_products[i]['id'] not in seen_ids:
                        products.append(v2_products[i])
                        seen_ids.add(v2_products[i]['id'])

            # Step 5: Generate response for user
            # Emitir evento de generación de respuesta
            await emit_progress(
                state=state,
                step_type=StepType.RESPONSE_GEN,
                status=StepStatus.STARTED,
                title="Preparando respuesta",
                description="Generando recomendaciones personalizadas...",
                details={"products_count": len(products)}
            )

            products_text = "\n".join([
                f"- {p['name']} (${p['price']:.2f}) - {p['category']} - {p['color']}"
                for p in products
            ])

            image_context = ""
            if image_description:
                image_context = f"""
The user also sent an image. You analyzed it and saw: {image_description[:300]}
Based on this image, you searched for similar products."""

            response_prompt = f"""You are a helpful shopping assistant. The user asked: "{user_message}"
{image_context}

I found these products (selected from multiple search methods):
{products_text}

IMPORTANT: Respond in the SAME LANGUAGE as the user's query.
- If the user wrote in Spanish, respond in Spanish
- If the user wrote in English, respond in English

Provide a friendly, helpful response presenting these products. Be concise but enthusiastic.
Mention key details like name, price, category, and color."""

            response = await llm.ainvoke([{"role": "user", "content": response_prompt}])
            response_content = response.content

            # Emitir evento de respuesta completada
            await emit_progress(
                state=state,
                step_type=StepType.RESPONSE_GEN,
                status=StepStatus.COMPLETED,
                title="Respuesta lista",
                description=f"Encontrados {len(products)} productos relevantes",
                details={"response_length": len(response_content)}
            )
        else:
            logger.warning("All search methods returned no products")
            products = []

            error_prompt = f"""The user asked: "{user_message}"

No products were found. Provide a polite apology in the SAME LANGUAGE as the user's query.
Keep it brief and suggest they try different terms."""

            error_response = await llm.ainvoke([{"role": "user", "content": error_prompt}])
            response_content = error_response.content

        total_time = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"✅ HYBRID SEMANTIC SEARCH NODE COMPLETE in {total_time:.2f}s")
        logger.info(f"   Final products: {len(products)}")
        logger.info(f"   V1 contributed: {sum(1 for p in products if p.get('search_method') == 'v1_terms')}")
        logger.info(f"   V2 contributed: {sum(1 for p in products if p.get('search_method') == 'v2_full_query')}")
        logger.info(f"   V3 contributed: {sum(1 for p in products if p.get('search_method') == 'v3_distinctive')} ← DISTINCTIVE")
        logger.info("=" * 80)

        return {
            "messages": [{"role": "assistant", "content": response_content}],
            "products_found": products,
            "search_method": "hybrid",
            "search_stats": stats,
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
