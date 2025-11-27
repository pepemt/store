"""Classifier node for intent classification"""
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import AgentState
from llm_config import llm
from metadata_cache import get_metadata_cache

logger = logging.getLogger(__name__)


async def classifier_node(state: AgentState) -> dict:
    """Classify user intent for routing"""
    messages = state["messages"]
    user_message = messages[-1].content if messages else ""

    # Build conversation history for context (last 6 messages max)
    history_context = ""
    if len(messages) > 1:
        recent_messages = messages[-7:-1]  # Get up to 6 previous messages (excluding current)
        history_lines = []
        for msg in recent_messages:
            role = getattr(msg, 'role', 'unknown') if hasattr(msg, 'role') else (
                msg.get('role', 'unknown') if isinstance(msg, dict) else 'unknown'
            )
            content = getattr(msg, 'content', str(msg)) if hasattr(msg, 'content') else (
                msg.get('content', str(msg)) if isinstance(msg, dict) else str(msg)
            )
            # Truncate long messages
            content_preview = content[:200] + "..." if len(content) > 200 else content
            history_lines.append(f"  {role}: {content_preview}")
        if history_lines:
            history_context = "\n\nRecent conversation history:\n" + "\n".join(history_lines)

    # Check for image description from current message OR from conversation context
    image_description = state.get("image_description")
    conversation_context = state.get("conversation_context", {})

    # If no current image description, check if there was a recent one in context
    if not image_description and conversation_context.get("last_image_description"):
        image_description = conversation_context.get("last_image_description")
        logger.info(f"Using image description from conversation context")

    if image_description:
        enriched_message = f"{user_message}\n\n[Imagen adjunta/reciente: {image_description}]"
    else:
        enriched_message = user_message

    # Get metadata cache for context
    metadata_cache = get_metadata_cache()
    metadata_context = metadata_cache.get_formatted_context()

    prompt = f"""Classify the user message into exactly ONE category. Respond with only the category name.
{history_context}

We sell these products:
{metadata_context}

Categories:
- product_search: User wants to FIND or BUY products similar to an image or description
  Examples: "busca algo similar", "quiero algo como esto", "recomiéndame algo así", "busco pantalón negro"
  Use this when user explicitly wants to search/buy products.

- product_recommendations: User wants GENERAL suggestions without specifics
  Examples: "what do you recommend?", "qué me sugieres?", "I need gift ideas"

- chat: User wants INFORMATION, DESCRIPTION, or general conversation
  Examples: "qué ves en la imagen?", "dime que ves", "describe esto", "qué es esto?", "hello", "hola"
  Use this when user asks WHAT something IS (description) rather than wanting to BUY it.

CRITICAL RULES FOR IMAGES:
- "qué ves", "dime que ves", "describe", "qué es esto" + image → chat (wants description)
- "busca similar", "quiero algo así", "recomiéndame productos" + image → product_search (wants to buy)
- Image alone without text → chat (ask what they want)

IMPORTANT:
- Questions about WHAT an item IS = chat
- Requests to FIND/BUY similar items = product_search
- Greetings and store questions = chat

Now classify this message:
Message: {enriched_message}
Category:"""

    # Use ainvoke for async consistency
    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    intent = response.content.strip().lower()

    valid_intents = ["product_search", "product_recommendations", "chat"]
    if intent not in valid_intents:
        intent = "chat"

    logger.info(f"Classified intent: {intent}")
    return {"intent": intent}
