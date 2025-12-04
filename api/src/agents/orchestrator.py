"""
Intelligent orchestrator for the unified agent architecture.

This module implements the ReAct (Reasoning + Acting) pattern with:
- orchestrator_node: Generates execution plans based on full context
- executor_node: Executes plans with parallel support
- response_generator_node: Generates final structured responses
"""

import logging
import json
import re
import asyncio
import time
import os
import importlib.util
from typing import Dict, Any, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from state import (
    UnifiedAgentState,
    ExecutionPlan,
    ExecutionStep,
    ImageData,
    ImageAnalysis,
    StructuredResponse,
    VariantSection,
    BudgetSummary,
    StepType,
    StepStatus,
    StepResult,
)
from llm_config import llm
from progress_utils import emit_progress

# Import from tools/ submodules using importlib to avoid circular import issues
# The naming conflict between tools.py and tools/ directory requires explicit path loading
_current_dir = os.path.dirname(os.path.abspath(__file__))

# Import from tools/budget.py
_budget_path = os.path.join(_current_dir, "tools", "budget.py")
_budget_spec = importlib.util.spec_from_file_location("tools_budget", _budget_path)
_budget_module = importlib.util.module_from_spec(_budget_spec)
_budget_spec.loader.exec_module(_budget_module)
parse_budget = _budget_module.parse_budget
calculate_budget_breakdown = _budget_module.calculate_budget_breakdown

# Import from tools/search.py
_search_path = os.path.join(_current_dir, "tools", "search.py")
_search_spec = importlib.util.spec_from_file_location("tools_search", _search_path)
_search_module = importlib.util.module_from_spec(_search_spec)
_search_spec.loader.exec_module(_search_module)
search_products = _search_module.search_products

# Import from tools/analyze.py
_analyze_path = os.path.join(_current_dir, "tools", "analyze.py")
_analyze_spec = importlib.util.spec_from_file_location("tools_analyze", _analyze_path)
_analyze_module = importlib.util.module_from_spec(_analyze_spec)
_analyze_spec.loader.exec_module(_analyze_module)
analyze_images = _analyze_module.analyze_images
compare_products = _analyze_module.compare_products

logger = logging.getLogger(__name__)


# -----------------------------
# System Prompts
# -----------------------------

ORCHESTRATOR_SYSTEM_PROMPT = """Eres el orquestador inteligente de Zenith, una tienda de ropa en línea.

TU ROL:
- Entender el contexto COMPLETO de lo que el usuario quiere
- Generar un plan de ejecución con las herramientas correctas
- Adaptarte dinámicamente según los resultados

HERRAMIENTAS DISPONIBLES:
1. search(query, filters, budget_usd, limit, search_reviews, review_need) - Búsqueda unificada de productos
   - search_reviews=true + review_need="texto" para buscar por NECESIDAD/PROPÓSITO basado en reviews de usuarios
   - Usa search_reviews cuando el usuario expresa una NECESIDAD subjetiva, no una descripción literal
   - Ejemplos de cuándo usar search_reviews=true:
     * "necesito algo elegante para una fiesta" → search_reviews=true, review_need="elegant formal party gala"
     * "busco ropa cómoda para estar en casa" → search_reviews=true, review_need="comfortable home casual"
     * "quiero algo que se vea premium" → search_reviews=true, review_need="premium luxury high quality"
2. analyze_images(images, context, type) - Análisis contextual de imágenes
3. compare(products, criteria) - Comparar N productos en M criterios
4. budget_calc(products) - Calcular desglose de presupuesto

⚠️ REGLA CRÍTICA PARA BÚSQUEDAS:
- TODAS las queries de búsqueda DEBEN estar en INGLÉS
- La base de datos de productos está indexada en inglés
- SIEMPRE traduce los términos de búsqueda al inglés
- Incluye sinónimos cuando sea útil
- SIEMPRE incluye género: men, women, boys, girls, unisex

EJEMPLOS DE TRADUCCIÓN:
- "pantalón de mezclilla negro para hombre" → "jeans denim trousers black men"
- "vestido rojo para mujer" → "dress red women"
- "playera con unicornio para niña" → "t-shirt unicorn girls kids"
- "sudadera con corazones rosa" → "hoodie sweatshirt hearts pink"
- "zapatos deportivos blancos" → "sneakers shoes sports white"

PRINCIPIOS CLAVE:
- Para NECESIDADES/PROPÓSITOS (MUY IMPORTANTE):
  * Cuando el usuario expresa QUÉ QUIERE LOGRAR o CÓMO QUIERE SENTIRSE, usa search_reviews=true
  * NO es lo mismo buscar "vestido negro" (descripción literal) que "algo elegante para fiesta" (necesidad)
  * Ejemplos de NECESIDADES (usar search_reviews=true):
    - "necesito algo elegante para una gala" → {"tool": "search", "params": {"search_reviews": true, "review_need": "elegant formal gala event", "query": "formal dress suit men women"}}
    - "busco ropa cómoda para trabajar" → {"tool": "search", "params": {"search_reviews": true, "review_need": "comfortable work office", "query": "casual comfortable workwear"}}
    - "quiero algo que se vea premium" → {"tool": "search", "params": {"search_reviews": true, "review_need": "premium luxury high quality", "query": "premium luxury clothing"}}
  * Ejemplos de DESCRIPCIONES LITERALES (NO usar search_reviews):
    - "busco un pantalón negro" → búsqueda normal
    - "quiero una camisa azul" → búsqueda normal

- Para IMÁGENES: TÚ decides qué extraer basado en la petición:
  * "busca algo similar" + imagen → extraer atributos para búsqueda (type="attributes")
  * "qué outfits puedo armar" + imagen → identificar items (type="outfit")
  * "dame un outfit" + imagen → usar type="outfit" para obtener component_queries
  * "compara estos" + imágenes → extraer para comparación (type="comparison")
  * Múltiples personas/items → type="items" y procesar cada uno

- CONTEXTO DE IMÁGENES PREVIAS (MUY IMPORTANTE):
  * El historial incluye "[IMAGEN ANALIZADA] ..." cuando el usuario envió imágenes antes
  * Cuando el usuario dice "busca mejor", "busca parecidos", "como el de la imagen", "similar al que te mostré":
    - NUNCA uses analyze_images si no hay imagen nueva (fallará)
    - USA DIRECTAMENTE el tool "search" con la query del historial
  * Ejemplo: Si el historial dice "Contenido detectado: orange floral long dress"
    → Genera directamente: {"tool": "search", "params": {"query": "orange floral long dress"}}
    → NO generes: {"tool": "analyze_images", ...} (no hay imagen que analizar)

- Para OUTFIT REQUESTS (cuando piden conjunto/outfit/look):
  * SIEMPRE usa analyze_images con type="outfit" primero
  * El análisis retornará component_queries con búsquedas separadas por componente (top, bottom, shoes, accessories)
  * SOLO genera pasos de búsqueda para componentes que SÍ EXISTAN en la imagen
  * NO asumas que todos los componentes estarán disponibles - usa SOLO los que el análisis detecte
  * Usa search_queries[N] como fallback si component_queries no tiene el componente específico

  Ejemplo CORRECTO (adapta según los componentes detectados):
  {
    "steps": [
      {"id": "step_1", "tool": "analyze_images", "params": {"type": "outfit"}, "depends_on": []},
      {"id": "step_2", "tool": "search", "params": {"query": "{step_1.analyses[0].component_queries.top[0]}", "limit": 3}, "depends_on": ["step_1"]},
      {"id": "step_3", "tool": "search", "params": {"query": "{step_1.analyses[0].component_queries.bottom[0]}", "limit": 3}, "depends_on": ["step_1"]}
    ]
  }

  Si un componente no está disponible, usa search_queries como fallback:
  {"query": "{step_1.analyses[0].search_queries[0]}"}

- Para PRESUPUESTO: Parsear cantidad Y moneda, convertir a USD
  * "500 pesos" → 500 MXN → ~$29 USD → filtrar por ese precio
  * El presupuesto es TOTAL, no por item (a menos que se especifique)

- Para COMPARACIONES (cuando el usuario quiere decidir entre opciones):
  * Detecta frases como: "cuál me conviene", "cuál es mejor", "qué me recomiendas", "compara", "diferencias entre"
  * Si el usuario dice "compara los que me mostraste" o similar, USA LOS PRODUCTOS ANTERIORES (previous_products)
  * Si hay previous_products disponibles y el usuario hace referencia a ellos, usa compare directamente SIN search
  * Solo busca nuevos productos si el usuario pide algo NUEVO

  Ejemplo cuando HAY previous_products y el usuario dice "compara esos":
  {
    "steps": [
      {"id": "step_1", "tool": "compare", "params": {"products": "USE_PREVIOUS_PRODUCTS", "criteria": ["price", "category", "color"]}, "depends_on": []}
    ]
  }

  Ejemplo cuando NO hay previous_products o el usuario pide algo nuevo:
  {
    "steps": [
      {"id": "step_1", "tool": "search", "params": {"query": "jacket coat men black", "limit": 5}, "depends_on": []},
      {"id": "step_2", "tool": "compare", "params": {"products": "{step_1.products}", "criteria": ["price", "category", "color"]}, "depends_on": ["step_1"]}
    ]
  }

  IMPORTANTE para compare:
  - Máximo 5 productos para comparar (evitar tablas muy anchas)
  - Solo usar criterios que EXISTAN en los productos: price, category, color, department
  - NO usar criterios inventados como "material", "warmth", "style" (no existen en la BD)

- Para VARIANTES: Si detectas múltiples personas/items/opciones:
  * Generar una variante por cada uno
  * Cada variante necesita title descriptivo y summary

- NUNCA fragmentes flujos - todo a través de tu plan de ejecución

FORMATO DE REFERENCIAS (MUY IMPORTANTE):
Cuando un paso depende de otro, usa esta sintaxis EXACTA para referenciar resultados:
- {step_1.analyses[0].search_queries[0]} - Primera query del análisis de imagen
- {step_1.analyses[0].attributes.color} - Color extraído de la imagen
- {step_1.products[0].name} - Nombre del primer producto

EJEMPLO CON IMAGEN Y BÚSQUEDAS:
Si el usuario envía una imagen y quiere encontrar ropa similar:
{
  "steps": [
    {"id": "step_1", "tool": "analyze_images", "params": {"type": "items", "context": "Extraer atributos de cada persona"}, "depends_on": []},
    {"id": "step_2", "tool": "search", "params": {"query": "{step_1.analyses[0].search_queries[0]}"}, "depends_on": ["step_1"]},
    {"id": "step_3", "tool": "search", "params": {"query": "{step_1.analyses[0].search_queries[1]}"}, "depends_on": ["step_1"]}
  ]
}

¡NO HAGAS ESTO! (INCORRECTO):
- {"query": "outfit similar a [atributos de persona 1]"} ← MAL, placeholder literal
- {"query": "buscar ropa para la persona de la imagen"} ← MAL, texto genérico sin referencia
- {"query": "ropa casual"} cuando no has analizado la imagen ← MAL, no esperas el análisis

SIEMPRE: Primero analyze_images, LUEGO usa {step_N.field} en los pasos siguientes.

FORMATO DE SALIDA:
Responde SOLO con un JSON válido:
{
  "reasoning": "Breve explicación de tu entendimiento",
  "requires_tools": true/false,
  "execution_plan": {
    "steps": [
      {
        "id": "step_1",
        "tool": "search|analyze_images|compare|budget_calc",
        "operation": "descripción de qué hacer",
        "params": {"param1": "value1"},
        "depends_on": []
      }
    ]
  },
  "direct_response": "respuesta si no se necesitan herramientas",
  "has_variants": false,
  "variant_count": 0
}

Si la consulta es un saludo o pregunta simple, usa requires_tools=false y direct_response.
"""

RESPONSE_GENERATOR_PROMPT = """Genera una respuesta amigable y estructurada basada en los resultados.

RESULTADOS DE EJECUCIÓN:
{execution_results}

CONSULTA ORIGINAL:
{original_query}

REGLAS:
1. Responde en el MISMO idioma que el usuario
2. Si hay productos, menciona los más relevantes con precio
3. Si hay variantes, estructura la respuesta para cada una
4. Si hay comparación, incluye la tabla markdown
5. Si hay presupuesto, muestra el desglose
6. Sé conciso pero informativo

Para respuestas con variantes, usa este formato JSON:
{{
  "type": "variants",
  "main_message": "mensaje principal",
  "variants": [
    {{
      "id": "variant_1",
      "title": "título descriptivo",
      "summary": "resumen breve",
      "content": {{...}},
      "is_expanded": true/false
    }}
  ]
}}

Para respuestas simples:
{{
  "type": "single",
  "main_message": "tu respuesta completa aquí"
}}
"""


# -----------------------------
# Tool Execution Functions
# -----------------------------

async def execute_tool(tool_name: str, params: Dict[str, Any], state: UnifiedAgentState) -> Any:
    """Execute a tool with the given parameters."""
    logger.info(f"Executing tool: {tool_name} with params: {params}")

    try:
        if tool_name == "search":
            # Build conversation context from messages (like the previous system)
            conversation_context = None
            messages = state.get("messages", [])
            if len(messages) > 1:
                recent_messages = messages[-5:-1]  # Last 4 messages
                history_lines = []
                for msg in recent_messages:
                    role = getattr(msg, 'role', 'unknown') if hasattr(msg, 'role') else 'unknown'
                    content = getattr(msg, 'content', str(msg)) if hasattr(msg, 'content') else str(msg)
                    content_preview = content[:300] + "..." if len(content) > 300 else content
                    history_lines.append(f"  {role}: {content_preview}")
                if history_lines:
                    conversation_context = "Recent conversation:\n" + "\n".join(history_lines)

            # Get image description with fallback to conversation context (like the previous system)
            image_description = state.get("image_description")
            conv_context = state.get("conversation_context", {})
            if not image_description and conv_context.get("last_image_description"):
                image_description = conv_context.get("last_image_description")
                logger.info("Using image description from conversation context")

            # Emit SEARCH_REFINE started event
            await emit_progress(
                state=state,
                step_type=StepType.SEARCH_REFINE,
                status=StepStatus.STARTED,
                title="Refinando búsqueda",
                description="Traduciendo y optimizando términos de búsqueda..."
            )

            # Execute search with state for progress events
            # The search_products function will emit SEARCH_PARALLEL events internally
            # Get limit from params, default to 15 for good variety
            requested_limit = params.get("limit", 15)
            # Ensure minimum of 10 products
            effective_limit = max(requested_limit, 10)

            result = await search_products(
                query=params.get("query"),
                filters=params.get("filters"),
                budget_usd=params.get("budget_usd"),
                limit=effective_limit,
                strategies=params.get("strategies", ["v1", "v2", "v3"]),
                search_reviews=params.get("search_reviews", False),
                review_need=params.get("review_need"),
                image_description=image_description,
                conversation_context=conversation_context,
                state=state,  # Pass state for progress events
            )

            # Emit search completed events with REAL times from result
            if "refinement" in result.get("strategies_used", []):
                await emit_progress(
                    state=state,
                    step_type=StepType.SEARCH_REFINE,
                    status=StepStatus.COMPLETED,
                    title="Query refinada",
                    description=f"Términos optimizados para búsqueda",
                    duration_ms=result.get("refine_time_ms", 0)  # REAL time
                )

            if "discrimination" in result.get("strategies_used", []):
                # Build description with review count if available
                review_count = result.get('review_count', 0)
                desc_parts = [f"V3:{result.get('v3_count', 0)}", f"V1:{result.get('v1_count', 0)}", f"V2:{result.get('v2_count', 0)}"]
                if review_count > 0:
                    desc_parts.append(f"Reviews:{review_count}")

                await emit_progress(
                    state=state,
                    step_type=StepType.DISCRIMINATOR,
                    status=StepStatus.COMPLETED,
                    title="Productos seleccionados",
                    description=" ".join(desc_parts),
                    details={
                        "distinctive_terms": result.get("distinctive_terms", []),
                        "v1_count": result.get("v1_count", 0),
                        "v2_count": result.get("v2_count", 0),
                        "v3_count": result.get("v3_count", 0),
                        "review_count": review_count,
                    },
                    duration_ms=result.get("discrimination_time_ms", 0)  # REAL time
                )

            return {
                "products": result["products"],
                "count": len(result["products"]),
                "search_method": result.get("search_method", "hybrid"),
                "distinctive_terms": result.get("distinctive_terms", []),
                "v1_count": result.get("v1_count", 0),
                "v2_count": result.get("v2_count", 0),
                "v3_count": result.get("v3_count", 0),
                "review_count": result.get("review_count", 0),
                "refine_time_ms": result.get("refine_time_ms", 0),
                "search_time_ms": result.get("search_time_ms", 0),
                "discrimination_time_ms": result.get("discrimination_time_ms", 0),
            }

        elif tool_name == "analyze_images":
            # DEBUG: Log state image info
            logger.info(f"=== ANALYZE_IMAGES DEBUG ===")
            logger.info(f"State has image_data: {bool(state.get('image_data'))}")
            logger.info(f"State image_data length: {len(state.get('image_data', '') or '')} chars")
            logger.info(f"State image_mime_type: {state.get('image_mime_type')}")
            logger.info(f"State has_image: {state.get('has_image')}")
            logger.info(f"Params keys: {list(params.keys())}")

            # Get images from state or params
            images_param = params.get("images") or []
            logger.info(f"images_param: {images_param}")

            images: List[ImageData] = []

            # Handle different image input formats
            for img in images_param:
                logger.info(f"Processing img: type={type(img).__name__}, value={str(img)[:50]}")
                if isinstance(img, str):
                    # If it's a string placeholder like "user_uploaded_image", get from state
                    if "user" in img.lower() or img == "user_uploaded_image" or img == "user_image":
                        if state.get("image_data"):
                            images.append({
                                "id": "img_user",
                                "data": state["image_data"],
                                "mime_type": state.get("image_mime_type", "image/jpeg")
                            })
                            logger.info(f"Added user image from state: {len(state['image_data'])} chars")
                        else:
                            logger.warning(f"Placeholder '{img}' but no image_data in state!")
                elif isinstance(img, dict) and img.get("data"):
                    images.append({
                        "id": img.get("id", f"img_{len(images)}"),
                        "data": img["data"],
                        "mime_type": img.get("mime_type", "image/jpeg")
                    })
                    logger.info(f"Added dict image: {len(img['data'])} chars")
                elif hasattr(img, 'data'):  # Already ImageData-like object
                    images.append(img)
                    logger.info(f"Added ImageData-like object")

            # Fallback: if no images resolved, use state image directly
            if not images and state.get("image_data"):
                images = [{
                    "id": "img_0",
                    "data": state["image_data"],
                    "mime_type": state.get("image_mime_type", "image/jpeg")
                }]
                logger.info(f"Used fallback: state image directly")

            logger.info(f"Total images to analyze: {len(images)}")

            if not images:
                logger.warning("No images found for analyze_images")
                return {"analyses": [], "error": "No images provided"}

            analyses = await analyze_images(
                images=images,
                analysis_context=params.get("context", "Analyze this image"),
                extraction_type=params.get("type", "auto")
            )
            return {"analyses": [a for a in analyses]}

        elif tool_name == "compare":
            products = params.get("products", [])

            # Handle USE_PREVIOUS_PRODUCTS - use products from previous turn
            if products == "USE_PREVIOUS_PRODUCTS" or (isinstance(products, str) and "PREVIOUS" in products.upper()):
                previous_products = state.get("previous_products", [])
                if previous_products:
                    products = previous_products
                    logger.info(f"Using {len(products)} previous products for comparison")
                else:
                    logger.warning("USE_PREVIOUS_PRODUCTS requested but no previous products available")
                    return {"comparison": {"markdown_table": "", "insights": {}, "recommendation": "No hay productos anteriores para comparar."}}

            result = await compare_products(
                products=products,
                criteria=params.get("criteria"),
                user_priorities=params.get("priorities")
            )
            # ComparisonResult is a TypedDict, access with dict notation
            return {
                "comparison": {
                    "markdown_table": result.get("markdown_table", ""),
                    "insights": result.get("insights", {}),
                    "recommendation": result.get("recommendation", "")
                }
            }

        elif tool_name == "budget_calc":
            products = params.get("products", [])

            # Validate products are actual objects, not unresolved strings
            valid_products = []
            for p in products:
                if isinstance(p, dict) and p.get("id"):
                    valid_products.append(p)
                elif isinstance(p, str):
                    logger.warning(f"budget_calc received string instead of product: {p[:80]}...")
                    # Skip invalid items
                else:
                    logger.warning(f"budget_calc received invalid item type: {type(p).__name__}")

            if not valid_products:
                # Fallback: try to get products from state
                valid_products = state.get("products_found", [])
                if valid_products:
                    logger.info(f"budget_calc using {len(valid_products)} products from state")
                else:
                    logger.warning("budget_calc: no valid products found")
                    return {"budget": {"error": "No valid products", "total": 0, "items": []}}

            budget_context = state.get("budget")
            result = calculate_budget_breakdown(valid_products, budget_context)
            return {"budget": result}

        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"error": str(e)}


# -----------------------------
# Graph Nodes
# -----------------------------

async def orchestrator_node(state: UnifiedAgentState) -> Dict[str, Any]:
    """
    Main orchestrator node that generates execution plans.

    Analyzes full context (messages, images, budget, history) and decides
    what tools to call and how to structure the response.
    """
    start_time = time.time()

    # Get conversation context
    messages = state.get("messages", [])
    if not messages:
        return {"response": "Hola, ¿en qué puedo ayudarte?"}

    # Extract user message
    last_message = messages[-1]
    user_message = last_message.content if hasattr(last_message, 'content') else str(last_message)

    logger.info(f"Orchestrator processing: {user_message[:100]}...")

    # Emit progress
    await emit_progress(
        state=state,
        step_type=StepType.ORCHESTRATOR,
        status=StepStatus.STARTED,
        title="Analizando solicitud",
        description="Entendiendo qué necesitas..."
    )

    # Build context for orchestrator
    context_parts = []

    # Check for budget in message
    budget = parse_budget(user_message)
    if budget:
        context_parts.append(f"PRESUPUESTO DETECTADO: {budget['amount']} {budget['currency']} = ${budget['amount_usd']:.2f} USD")

    # Check for current image
    has_image = state.get("has_image", False) or state.get("image_data")
    if has_image:
        context_parts.append("IMAGEN ADJUNTA: El usuario envió una imagen en este turno")
    # Note: Previous image descriptions are now in the conversation history as [Análisis de imagen: ...]
    # The LLM will see them naturally in the messages

    # Check for previous products (from last turn)
    previous_products = state.get("previous_products", [])
    if previous_products:
        product_names = [p.get("name", "?") for p in previous_products[:5]]
        context_parts.append(f"PRODUCTOS ANTERIORES: {len(previous_products)} productos mostrados previamente: {', '.join(product_names)}")
        context_parts.append("Si el usuario quiere comparar 'esos' o 'los que mostraste', usa compare con products='USE_PREVIOUS_PRODUCTS'")

    context_str = "\n".join(context_parts) if context_parts else "Sin contexto adicional"

    # Build conversation history for LLM context (last 6 messages before current)
    conversation_history = []
    for msg in messages[:-1]:  # All except current message
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
        else:
            role = getattr(msg, "role", "unknown")
            content = getattr(msg, "content", str(msg))

        # Keep image analysis messages in full, truncate others
        if "[IMAGEN ANALIZADA]" in content or "[Análisis de imagen" in content:
            # This is important context - keep it
            conversation_history.append(f"[CONTEXTO]: {content}")
        elif len(content) > 200:
            content = content[:200] + "..."
            conversation_history.append(f"{role}: {content}")
        else:
            conversation_history.append(f"{role}: {content}")

    # Keep last 6 messages for context
    history_str = "\n".join(conversation_history[-6:]) if conversation_history else ""

    # Build orchestrator prompt
    orchestrator_prompt = f"""
{ORCHESTRATOR_SYSTEM_PROMPT}

CONTEXTO ACTUAL:
{context_str}

MENSAJE DEL USUARIO:
{user_message}

Genera tu plan de ejecución como JSON:
"""

    try:
        # Build the full prompt with history
        prompt_parts = []
        if history_str:
            prompt_parts.append(f"HISTORIAL DE CONVERSACIÓN:\n{history_str}")
        if context_str and context_str != "Sin contexto adicional":
            prompt_parts.append(f"CONTEXTO ACTUAL:\n{context_str}")
        prompt_parts.append(f"MENSAJE ACTUAL DEL USUARIO:\n{user_message}")

        full_prompt = "\n\n".join(prompt_parts)

        # Call LLM with conversation history
        response = await llm.ainvoke([
            SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
            HumanMessage(content=full_prompt)
        ])

        response_text = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"Orchestrator response: {response_text[:500]}")

        # Parse JSON response
        plan_json = _extract_json(response_text)

        elapsed = time.time() - start_time

        await emit_progress(
            state=state,
            step_type=StepType.ORCHESTRATOR,
            status=StepStatus.COMPLETED,
            title="Plan generado",
            description=plan_json.get("reasoning", "Plan listo")[:80],
            duration_ms=int(elapsed * 1000)
        )

        # If no tools needed, return direct response
        if not plan_json.get("requires_tools", True):
            return {
                "response": plan_json.get("direct_response", ""),
                "execution_plan": None
            }

        # Store budget in state if found
        updates = {
            "execution_plan": plan_json.get("execution_plan"),
            "user_intent_summary": plan_json.get("reasoning", ""),
        }

        if budget:
            updates["budget"] = budget

        return updates

    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        await emit_progress(
            state=state,
            step_type=StepType.ORCHESTRATOR,
            status=StepStatus.ERROR,
            title="Error",
            description=str(e)[:80]
        )
        return {"response": "Lo siento, ocurrió un error procesando tu solicitud."}


async def executor_node(state: UnifiedAgentState) -> Dict[str, Any]:
    """
    Executor node that runs the orchestrator's plan.

    Uses topological ordering to respect dependencies:
    - Steps with no dependencies execute first
    - Steps wait for their dependencies to complete
    - Independent steps run in parallel
    """
    start_time = time.time()

    plan = state.get("execution_plan")
    if not plan:
        logger.info("No execution plan, skipping executor")
        return {}

    steps_list = plan.get("steps", [])
    if not steps_list:
        logger.info("Empty steps list, skipping executor")
        return {}

    logger.info(f"Executor running plan with {len(steps_list)} steps")

    await emit_progress(
        state=state,
        step_type=StepType.EXECUTOR,
        status=StepStatus.STARTED,
        title="Ejecutando plan",
        description=f"Procesando {len(steps_list)} pasos..."
    )

    # Build step dictionary for easy lookup
    steps = {s["id"]: s for s in steps_list}
    results = {}
    executed = set()

    # Execute using topological order (respecting dependencies)
    max_iterations = len(steps) + 5  # Safety limit
    iteration = 0

    while len(executed) < len(steps) and iteration < max_iterations:
        iteration += 1

        # Find steps that are ready (all dependencies satisfied)
        ready = []
        for step_id, step in steps.items():
            if step_id in executed:
                continue
            deps = step.get("depends_on", [])
            if all(d in executed for d in deps):
                ready.append(step)

        if not ready:
            # No steps ready but not all executed - deadlock or missing dependencies
            pending = [sid for sid in steps if sid not in executed]
            logger.error(f"Deadlock detectado: pasos pendientes {pending} pero ninguno listo")
            break

        # Log which steps will run
        logger.info(f"Ejecutando {len(ready)} paso(s) en paralelo: {[s['id'] for s in ready]}")

        # Execute ready steps in parallel
        tasks = []
        step_task_map = []  # Track which steps have valid tasks

        for step in ready:
            # Resolve parameters that reference previous results
            resolved_params, unresolved_refs = _resolve_params(step.get("params", {}), results)

            # Check if there are still unresolved placeholders
            # Only check strings that look like unresolved references (not JSON)
            def is_unresolved_ref(v):
                if not isinstance(v, str):
                    return False
                # Look for patterns like {step_X.field} that weren't resolved
                return bool(re.search(r'\{step_\d+\.[^}]+\}', v))

            has_unresolved = any(is_unresolved_ref(v) for v in resolved_params.values())

            if has_unresolved:
                logger.error(f"Step {step['id']} SKIPPED: unresolved refs {unresolved_refs}")
                logger.error(f"  Params after resolution: {resolved_params}")
                results[step["id"]] = {
                    "error": f"Unresolved references: {unresolved_refs}",
                    "skipped": True,
                    "unresolved_refs": unresolved_refs
                }
                executed.add(step["id"])
                continue

            logger.info(f"  {step['id']}: {step['tool']} con params={resolved_params}")
            tasks.append(execute_tool(step["tool"], resolved_params, state))
            step_task_map.append(step)

        # Run all valid tasks in parallel
        if tasks:
            group_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results and mark as executed
            for idx, (step, result) in enumerate(zip(step_task_map, group_results)):
                if isinstance(result, Exception):
                    logger.error(f"Step {step['id']} failed: {result}")
                    results[step["id"]] = {"error": str(result)}
                else:
                    # Ensure result is a dict
                    if not isinstance(result, dict):
                        result = {"value": result}

                    # Add resolved query to result for better display
                    resolved_params, _ = _resolve_params(step.get("params", {}), results)
                    if resolved_params.get("query"):
                        result["resolved_query"] = resolved_params["query"]

                    results[step["id"]] = result
                    logger.info(f"  {step['id']} completado: {type(result).__name__}")
                executed.add(step["id"])

    elapsed = time.time() - start_time

    await emit_progress(
        state=state,
        step_type=StepType.EXECUTOR,
        status=StepStatus.COMPLETED,
        title="Ejecución completa",
        description=f"{len(executed)}/{len(steps)} pasos en {elapsed:.1f}s",
        duration_ms=int(elapsed * 1000)
    )

    # Collect all products from results
    all_products = []
    image_description = None

    for step_id, result in results.items():
        if isinstance(result, dict):
            if "products" in result:
                all_products.extend(result["products"])

            # Extract image description from analyze_images results
            if "analyses" in result and result["analyses"]:
                analysis = result["analyses"][0]

                # Only use description if it's real content, not a fallback
                GENERIC_FALLBACKS = ["women dress", "clothing fashion", "women dress formal"]

                if analysis.get("description") and not analysis.get("parse_error"):
                    # Real description from vision model
                    image_description = analysis["description"]
                    logger.info(f"Extracted real image_description: {image_description[:100]}...")
                elif analysis.get("search_queries"):
                    queries = analysis["search_queries"]
                    # Only save if queries are specific, not generic fallbacks
                    if queries and queries[0] not in GENERIC_FALLBACKS:
                        image_description = f"Imagen analizada - buscar: {', '.join(queries[:3])}"
                        logger.info(f"Extracted search queries as description: {image_description}")

    logger.info(f"Executor completado: {len(executed)} pasos, {len(all_products)} productos")

    result_state = {
        "execution_results": results,
        "products_found": all_products[:20]
    }

    # Add image_description if found
    if image_description:
        result_state["image_description"] = image_description

    return result_state


async def response_generator_node(state: UnifiedAgentState) -> Dict[str, Any]:
    """
    Response generator that creates the final structured response.

    Uses execution results to build a user-friendly response with variants
    if applicable.
    """
    start_time = time.time()

    # If there's already a response (from direct response path)
    if state.get("response"):
        await emit_progress(
            state=state,
            step_type=StepType.RESPONSE_GEN,
            status=StepStatus.COMPLETED,
            title="Respuesta lista",
            description="Usando respuesta directa",
            duration_ms=0
        )
        return {}

    execution_results = state.get("execution_results", {})
    messages = state.get("messages", [])

    # Get original query
    original_query = ""
    if messages:
        last_msg = messages[-1]
        original_query = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)

    logger.info(f"Generating response for: {original_query[:100]}...")

    await emit_progress(
        state=state,
        step_type=StepType.RESPONSE_GEN,
        status=StepStatus.STARTED,
        title="Generando respuesta",
        description="Preparando resultados..."
    )

    # Get products from state
    products = state.get("products_found", [])

    # If no products and no meaningful results, generate dynamic error message with LLM
    if not products and not execution_results:
        try:
            error_prompt = f"""El usuario preguntó: "{original_query}"

No se encontraron productos. Genera una disculpa AMABLE en el MISMO IDIOMA que el usuario.
Mantenlo breve y sugiere que intente con términos diferentes.
NO uses formato de lista. Responde de forma natural y conversacional."""

            error_response = await llm.ainvoke([HumanMessage(content=error_prompt)])
            error_text = error_response.content if hasattr(error_response, 'content') else str(error_response)
        except Exception:
            error_text = "Lo siento, no encontré resultados para tu búsqueda. ¿Podrías intentar con otros términos?"

        elapsed = time.time() - start_time
        await emit_progress(
            state=state,
            step_type=StepType.RESPONSE_GEN,
            status=StepStatus.COMPLETED,
            title="Sin resultados",
            description="No se encontraron productos",
            duration_ms=int(elapsed * 1000)
        )
        return {"response": error_text}

    # If we have products, generate an expressive response with LLM
    if products:
        # Separate products by source (reviews vs semantic search)
        review_products = [p for p in products if p.get('from_reviews')]
        semantic_products = [p for p in products if not p.get('from_reviews')]

        # Build product list for LLM context (show all products found)
        products_text = ""

        if review_products:
            review_text = "\n".join([
                f"- {p.get('name', 'Producto')} (${p.get('price', 0):.2f}) - {p.get('category', '')} - Opinión: \"{p.get('evidence_review', '')[:100]}...\""
                for p in review_products[:8]
            ])
            products_text += f"\n🗣️ BASADOS EN OPINIONES DE USUARIOS ({len(review_products)} productos):\n{review_text}"

        if semantic_products:
            semantic_text = "\n".join([
                f"- {p.get('name', 'Producto')} (${p.get('price', 0):.2f}) - {p.get('category', '')} - {p.get('color', '')}"
                for p in semantic_products[:8]
            ])
            products_text += f"\n\n🔍 POR BÚSQUEDA SEMÁNTICA ({len(semantic_products)} productos):\n{semantic_text}"

        # Check for image context
        image_context = ""
        image_description = state.get("image_description")
        if image_description:
            image_context = f"\nEl usuario también envió una imagen. La analizaste y viste: {image_description[:300]}\nBasándote en esta imagen, buscaste productos similares."

        # Context about review-based results
        review_context = ""
        if review_products:
            review_context = f"""
IMPORTANTE SOBRE PRODUCTOS DE OPINIONES:
- {len(review_products)} productos fueron encontrados basándose en opiniones de otros usuarios
- Estos productos son recomendados porque otros clientes los describieron de forma similar a lo que busca el usuario
- DEBES mencionar que estos productos vienen recomendados por opiniones de usuarios reales
- Puedes citar brevemente alguna opinión relevante si es apropiado"""

        # Build expressive prompt (like the previous system)
        response_prompt = f"""Eres un asistente de compras amigable y entusiasta. El usuario preguntó: "{original_query}"
{image_context}

Encontré estos productos:{products_text}
{review_context}

IMPORTANTE: Responde en el MISMO IDIOMA que el usuario.
- Si el usuario escribió en español, responde en español
- Si el usuario escribió en inglés, responde en inglés
- Si el usuario envió una imagen, reconoce que la viste y entendiste
- Si hay productos basados en opiniones, MENCIONA que fueron recomendados por otros usuarios

Proporciona una respuesta amigable y útil presentando estos productos. Sé conciso pero ENTUSIASTA.
Menciona detalles clave como nombre, precio, categoría y color.
NO uses formato de lista con viñetas, escribe de forma natural y conversacional."""

        try:
            response = await llm.ainvoke([
                HumanMessage(content=response_prompt)
            ])
            response_text = response.content if hasattr(response, 'content') else str(response)
        except Exception as llm_error:
            logger.warning(f"LLM response generation failed: {llm_error}, using fallback")
            # Fallback to simple list if LLM fails (show more products)
            product_list = [f"- **{p.get('name', 'Producto')}** ({p.get('color', '')}) - ${p.get('price', 0):.2f}" for p in products[:15]]
            response_text = f"Encontré {len(products)} productos para ti:\n\n" + "\n".join(product_list)

        elapsed = time.time() - start_time

        await emit_progress(
            state=state,
            step_type=StepType.RESPONSE_GEN,
            status=StepStatus.COMPLETED,
            title="Respuesta lista",
            description=f"Encontrados {len(products)} productos",
            duration_ms=int(elapsed * 1000)
        )

        # Build step_results for multi-step display
        step_results = None
        outfit_components = None
        comparison_table = None

        if execution_results and _is_multi_step_request(state):
            step_results = _build_step_results(execution_results, state.get("execution_plan"))

            # Check for outfit request
            if _is_outfit_request(state):
                outfit_components = _build_outfit_components(execution_results)

        # Check for comparison results
        for step_id, result in (execution_results or {}).items():
            if isinstance(result, dict) and result.get("comparison"):
                comparison = result["comparison"]
                comparison_table = {
                    "markdown_table": comparison.get("markdown_table", ""),
                    "insights": comparison.get("insights", []),
                    "recommendation": comparison.get("recommendation", "")
                }
                logger.info(f"Found comparison table with {len(comparison.get('insights', []))} insights")
                break

        # Build structured response
        response_type = "comparison" if comparison_table else ("multi_step" if step_results else "single")
        structured_response: StructuredResponse = {
            "type": response_type,
            "main_message": response_text,
            "products": products,
        }

        # Add separated products for frontend display
        if review_products:
            structured_response["review_products"] = review_products
            structured_response["review_count"] = len(review_products)

        if semantic_products:
            structured_response["semantic_products"] = semantic_products
            structured_response["semantic_count"] = len(semantic_products)

        if step_results:
            structured_response["step_results"] = step_results

        if outfit_components:
            structured_response["outfit_components"] = outfit_components

        if comparison_table:
            structured_response["comparison_table"] = comparison_table

        return {
            "response": response_text,
            "products_found": products,
            "structured_response": structured_response
        }

    # Build response using LLM only if we don't have simple products
    try:
        prompt = RESPONSE_GENERATOR_PROMPT.format(
            execution_results=json.dumps(execution_results, indent=2, default=str)[:3000],
            original_query=original_query
        )

        response = await llm.ainvoke([
            SystemMessage(content="Eres un asistente de compras amigable. Responde de forma concisa y útil."),
            HumanMessage(content=prompt)
        ])

        response_text = response.content if hasattr(response, 'content') else str(response)

        # Try to parse as structured response
        structured = _extract_json(response_text)

        elapsed = time.time() - start_time

        await emit_progress(
            state=state,
            step_type=StepType.RESPONSE_GEN,
            status=StepStatus.COMPLETED,
            title="Respuesta lista",
            description="Respuesta generada exitosamente",
            duration_ms=int(elapsed * 1000)
        )

        # Build final response
        if structured.get("type") == "variants":
            return {
                "structured_response": structured,
                "response": structured.get("main_message", "")
            }
        else:
            # Use main_message or direct_response or the raw text
            final_response = (
                structured.get("main_message") or
                structured.get("direct_response") or
                response_text
            )
            return {"response": final_response}

    except Exception as e:
        logger.error(f"Response generation error: {e}", exc_info=True)
        elapsed = time.time() - start_time
        await emit_progress(
            state=state,
            step_type=StepType.RESPONSE_GEN,
            status=StepStatus.ERROR,
            title="Error",
            description=f"Error: {str(e)[:50]}",
            duration_ms=int(elapsed * 1000)
        )
        return {"response": "Lo siento, hubo un error al procesar tu solicitud. Por favor intenta de nuevo."}


def should_continue(state: UnifiedAgentState) -> str:
    """
    Determine if the orchestrator should continue or generate response.

    Returns:
        "refine" to loop back to orchestrator
        "generate" to proceed to response generation
    """
    # Check if we have a direct response
    if state.get("response"):
        return "generate"

    # Check if we have execution results
    if state.get("execution_results"):
        return "generate"

    # Check iteration count
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 5)

    if iteration >= max_iterations:
        logger.warning(f"Max iterations ({max_iterations}) reached")
        return "generate"

    return "refine"


# -----------------------------
# Helper Functions
# -----------------------------

def _extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from text response."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in code block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any JSON object
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Return text as response
    return {"requires_tools": False, "direct_response": text}


def _resolve_params(params: Dict[str, Any], results: Dict[str, Any]) -> tuple:
    """
    Resolve parameter references like {step_1.analyses[0].search_queries[0]}.

    Supports:
    - Simple references: {step_1.products}
    - Array indices: {step_1.analyses[0].search_queries[0]}
    - Partial strings: "Query: {step_1.analyses[0].search_queries[0]}"
    - Fallback to search_queries when component_queries.X doesn't exist

    Args:
        params: Parameters with potential references
        results: Results from previous steps

    Returns:
        Tuple of (resolved_params, list_of_unresolved_references)
    """
    resolved = {}
    unresolved_refs = []

    def resolve_reference(ref: str) -> tuple:
        """
        Resolve a single reference string like 'step_1.analyses[0].search_queries[0]'.
        Returns (value, success_bool).
        """
        # Normalize: convert [N] to .N for easier parsing
        # step_1.analyses[0].search_queries[0] -> step_1.analyses.0.search_queries.0
        normalized = ref.replace('][', '.').replace('[', '.').replace(']', '')
        parts = normalized.split('.')

        if not parts:
            return None, False

        step_id = parts[0]
        if step_id not in results:
            logger.warning(f"Reference failed: {step_id} not in results (available: {list(results.keys())})")
            return None, False

        current = results[step_id]

        for i, part in enumerate(parts[1:], 1):
            if part.isdigit():
                # Array index
                idx = int(part)
                if isinstance(current, list):
                    if idx < len(current):
                        current = current[idx]
                    elif len(current) > 0:
                        # Fallback: use last available element if index out of range
                        logger.info(f"Index {idx} out of range, using index 0 as fallback for ref '{ref}'")
                        current = current[0]
                    else:
                        logger.warning(f"Empty list for ref '{ref}'")
                        return None, False
                else:
                    logger.warning(f"Expected list but got {type(current).__name__} for index {idx} in ref '{ref}'")
                    return None, False
            elif isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    # Try fallback for component_queries: if component_queries.X doesn't exist, use search_queries
                    if part == "component_queries" and "search_queries" in current:
                        logger.info(f"Fallback: component_queries not found, using search_queries")
                        # Return first search_query as fallback
                        sq = current.get("search_queries", [])
                        if sq:
                            return sq[0], True
                        return None, False
                    # For component types (top, bottom, shoes, accessories), try search_queries fallback
                    if part in ["top", "bottom", "shoes", "accessories"]:
                        # We're trying to access component_queries.X but it doesn't exist
                        # Fallback to search_queries
                        parent = results[step_id]
                        if "analyses" in parent and parent["analyses"]:
                            analysis = parent["analyses"][0]
                            sq = analysis.get("search_queries", [])
                            if sq:
                                logger.info(f"Fallback: component_queries.{part} not found, using search_queries[0]")
                                return sq[0], True
                    logger.warning(f"Field '{part}' not in dict (available: {list(current.keys())[:5]}...) in ref '{ref}'")
                    return None, False
            else:
                logger.warning(f"Cannot access '{part}' on {type(current).__name__} in ref '{ref}'")
                return None, False

        return current, True

    for key, value in params.items():
        if isinstance(value, str):
            # Check if the entire value is a single reference {step_X.field}
            single_ref_match = re.fullmatch(r'\{([^}]+)\}', value.strip())
            if single_ref_match:
                # Entire value is a reference - resolve and keep original type
                ref = single_ref_match.group(1)
                resolved_value, success = resolve_reference(ref)
                if success:
                    resolved[key] = resolved_value  # Keep as list/dict, don't stringify
                else:
                    unresolved_refs.append(ref)
                    resolved[key] = value  # Keep original
            else:
                # Value contains references mixed with text - stringify resolved values
                def replace_ref(match):
                    ref = match.group(1)
                    resolved_value, success = resolve_reference(ref)

                    if not success:
                        unresolved_refs.append(ref)
                        return match.group(0)  # Keep original if can't resolve

                    if isinstance(resolved_value, (dict, list)):
                        return json.dumps(resolved_value)
                    return str(resolved_value)

                # Replace all {references} in the string
                resolved[key] = re.sub(r'\{([^}]+)\}', replace_ref, value)
        elif isinstance(value, list):
            # Handle list of potential references
            resolved_list = []
            for item in value:
                if isinstance(item, str) and item.startswith('{') and item.endswith('}'):
                    ref = item[1:-1]  # Remove braces
                    resolved_value, success = resolve_reference(ref)
                    if success:
                        resolved_list.append(resolved_value)
                    else:
                        unresolved_refs.append(ref)
                        resolved_list.append(item)  # Keep original
                else:
                    resolved_list.append(item)
            resolved[key] = resolved_list
        else:
            resolved[key] = value

    return resolved, unresolved_refs


# -----------------------------
# Step Results Helper Functions
# -----------------------------

def _is_multi_step_request(state: UnifiedAgentState) -> bool:
    """Detect if this is a multi-step request that should show step results."""
    # Check if there's an execution plan with multiple steps
    plan = state.get("execution_plan")
    if plan and plan.get("steps"):
        return len(plan["steps"]) > 1
    return False


def _is_outfit_request(state: UnifiedAgentState) -> bool:
    """Detect if user requested an outfit."""
    messages = state.get("messages", [])
    if not messages:
        return False

    last_msg = messages[-1]
    content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
    content_lower = content.lower()

    outfit_keywords = [
        "outfit", "conjunto", "look", "dame un", "arma un",
        "combina", "qué me pongo", "como vestir", "vestimenta",
        "atuendo", "combinación"
    ]
    return any(kw in content_lower for kw in outfit_keywords)


def _build_step_results(execution_results: Dict[str, Any], execution_plan: Optional[Dict] = None) -> List[StepResult]:
    """Convert execution results to displayable step results."""
    step_results = []

    # Get step info from plan if available
    step_info = {}
    if execution_plan and execution_plan.get("steps"):
        for step in execution_plan["steps"]:
            step_info[step["id"]] = {
                "tool": step.get("tool", ""),
                "operation": step.get("operation", ""),
                "params": step.get("params", {})
            }

    for step_id in sorted(execution_results.keys()):
        result = execution_results[step_id]
        if not isinstance(result, dict):
            continue

        # Determine status
        if result.get("error"):
            status = "error"
        elif result.get("skipped"):
            status = "skipped"
        else:
            status = "completed"

        # Generate title based on query or operation
        info = step_info.get(step_id, {})
        title = _generate_step_title(step_id, result, info)

        # Generate description
        description = _generate_step_description(result, info)

        step_result: StepResult = {
            "id": step_id,
            "title": title,
            "description": description,
            "status": status
        }

        # Add products if present (show more products for better display)
        if result.get("products"):
            step_result["products"] = result["products"][:8]  # Increased limit

        # Add analysis if present
        if result.get("analyses"):
            analyses = result["analyses"]
            if analyses and len(analyses) > 0:
                step_result["analysis"] = analyses[0]

        # Add error if present
        if result.get("error"):
            step_result["error"] = str(result["error"])

        # Add query used for this search (helpful for display)
        if info.get("params", {}).get("query"):
            step_result["search_query"] = info["params"]["query"]

        step_results.append(step_result)

    return step_results


def _generate_step_title(step_id: str, result: Dict, step_info: Dict) -> str:
    """Generate a descriptive title for a step based on query or operation."""
    if result.get("analyses"):
        return "📸 Análisis de imagen"

    if result.get("products"):
        count = len(result["products"])

        # Get query - prefer resolved_query from result, fallback to params
        query = result.get("resolved_query", "")
        if not query:
            params = step_info.get("params", {})
            query = params.get("query", "")

        operation = step_info.get("operation", "").lower()

        # Combine query and operation for better detection
        search_text = f"{query} {operation}".lower()

        # Detect component type
        component_label = _infer_component_label(search_text)
        if component_label:
            return f"🔍 {component_label} ({count})"

        # Show truncated query if available (and not a placeholder)
        if query and '{' not in query:
            display_query = query[:25] + "..." if len(query) > 25 else query
            return f"🔍 {display_query} ({count})"

        return f"🔍 Productos encontrados ({count})"

    if result.get("error"):
        return "❌ Paso con error"

    if result.get("skipped"):
        return "⏭️ Paso omitido"

    if result.get("budget"):
        return "💰 Cálculo de presupuesto"

    if result.get("comparison"):
        return "⚖️ Comparación de productos"

    return f"Paso {step_id}"


def _infer_component_label(text: str) -> Optional[str]:
    """Infer the outfit component label from search text."""
    if not text:
        return None

    text_lower = text.lower()

    # Outerwear (highest priority - coats, jackets, blazers)
    if any(kw in text_lower for kw in ["coat", "jacket", "blazer", "cardigan", "outerwear", "abrigo", "saco", "chaqueta"]):
        return "Abrigos / Sacos"

    # Tops (shirts, blouses, sweaters)
    if any(kw in text_lower for kw in ["blouse", "blusa"]):
        return "Blusas"
    if any(kw in text_lower for kw in ["shirt", "camisa"]):
        return "Camisas"
    if any(kw in text_lower for kw in ["sweater", "suéter", "jersey"]):
        return "Suéteres"
    if any(kw in text_lower for kw in ["top", "arriba"]):
        return "Partes de arriba"

    # Bottoms
    if any(kw in text_lower for kw in ["skirt", "falda"]):
        return "Faldas"
    if any(kw in text_lower for kw in ["pants", "jeans", "trousers", "pantalón", "pantalones"]):
        return "Pantalones"
    if any(kw in text_lower for kw in ["shorts", "short"]):
        return "Shorts"
    if any(kw in text_lower for kw in ["bottom", "abajo"]):
        return "Partes de abajo"

    # Shoes
    if any(kw in text_lower for kw in ["boots", "botas"]):
        return "Botas"
    if any(kw in text_lower for kw in ["heels", "tacones"]):
        return "Tacones"
    if any(kw in text_lower for kw in ["sneakers", "tenis"]):
        return "Tenis"
    if any(kw in text_lower for kw in ["shoes", "shoe", "zapatos", "zapato", "footwear"]):
        return "Zapatos"

    # Accessories
    if any(kw in text_lower for kw in ["bag", "handbag", "purse", "bolso", "bolsa", "cartera"]):
        return "Bolsos"
    if any(kw in text_lower for kw in ["hat", "sombrero", "gorra"]):
        return "Sombreros"
    if any(kw in text_lower for kw in ["scarf", "bufanda"]):
        return "Bufandas"
    if any(kw in text_lower for kw in ["jewelry", "joyería", "necklace", "collar", "earring", "arete"]):
        return "Joyería"
    if any(kw in text_lower for kw in ["belt", "cinturón"]):
        return "Cinturones"
    if any(kw in text_lower for kw in ["accessories", "accesorios"]):
        return "Accesorios"

    # Dresses
    if any(kw in text_lower for kw in ["dress", "vestido"]):
        return "Vestidos"

    return None


def _generate_step_description(result: Dict, step_info: Dict) -> str:
    """Generate a description for a step result."""
    operation = step_info.get("operation", "")

    if result.get("error"):
        return f"Error: {result['error'][:100]}"

    if result.get("skipped"):
        refs = result.get("unresolved_refs", [])
        if refs:
            return f"Omitido por referencias no resueltas: {', '.join(refs[:2])}"
        return "Paso omitido"

    if result.get("analyses"):
        analyses = result["analyses"]
        if analyses:
            first = analyses[0]
            # Show component_queries if available
            comp_queries = first.get("component_queries", {})
            if comp_queries:
                components = list(comp_queries.keys())
                return f"Componentes detectados: {', '.join(components)}"
            queries = first.get("search_queries", [])
            if queries:
                return f"Queries generadas: {', '.join(queries[:2])}"
            return "Imagen analizada"
        return "Sin resultados de análisis"

    if result.get("products"):
        count = len(result["products"])
        # Show the query used
        query = result.get("resolved_query", "")
        if query and '{' not in query:
            truncated = query[:40] + "..." if len(query) > 40 else query
            return f"Búsqueda: '{truncated}' → {count} productos"
        return f"{count} productos encontrados"

    if operation:
        return operation[:100]

    return "Completado"


def _build_outfit_components(execution_results: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Build outfit components from execution results."""
    components = {
        "top": [],
        "bottom": [],
        "shoes": [],
        "accessories": []
    }

    # Map steps to components based on order or content
    # Convention: step_2=top, step_3=bottom, step_4=shoes, step_5=accessories
    step_component_map = {
        "step_2": "top",
        "step_3": "bottom",
        "step_4": "shoes",
        "step_5": "accessories"
    }

    for step_id, component in step_component_map.items():
        if step_id in execution_results:
            result = execution_results[step_id]
            if isinstance(result, dict) and result.get("products"):
                components[component] = result["products"][:5]

    # Filter empty components
    return {k: v for k, v in components.items() if v}
