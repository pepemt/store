"""Chat node for general conversation"""
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import AgentState
from llm_config import llm

logger = logging.getLogger(__name__)



async def chat_node(state: AgentState) -> dict:
    """Handle general chat with e-commerce context"""
    messages = state["messages"]
    user_message = messages[-1].content if messages else ""

    # Get image description from current state or conversation context
    image_description = state.get("image_description")
    conversation_context = state.get("conversation_context", {})

    # If no current image description, check context for recent one
    if not image_description and conversation_context.get("last_image_description"):
        image_description = conversation_context.get("last_image_description")
        logger.info("Chat node: using image description from conversation context")

    # Build context-aware system prompt
    system_prompt = """Eres un asistente amigable de Zenith, una tienda de ropa en línea.

Tu rol es:
- Saludar y ayudar a los clientes de manera amable
- Responder preguntas generales sobre la tienda
- Guiar a los clientes hacia la búsqueda de productos o recomendaciones
- Si el usuario envía una imagen, puedes ver y describir lo que muestra
- Mantener el contexto de la conversación y recordar mensajes anteriores
- Ser breve y conversacional

Si el cliente te pregunta sobre productos específicos o quiere recomendaciones, sugiéreles que te digan qué están buscando.

Responde de manera natural y amigable."""

    # Build conversation with full history (up to last 10 messages)
    conversation = [{"role": "system", "content": system_prompt}]

    # Add conversation history (excluding the current message, last 10 exchanges)
    history_messages = messages[:-1] if len(messages) > 1 else []
    # Limit to last 10 messages to avoid context overflow
    history_messages = history_messages[-10:]

    for msg in history_messages:
        role = getattr(msg, 'role', 'user') if hasattr(msg, 'role') else (
            msg.get('role', 'user') if isinstance(msg, dict) else 'user'
        )
        content = getattr(msg, 'content', str(msg)) if hasattr(msg, 'content') else (
            msg.get('content', str(msg)) if isinstance(msg, dict) else str(msg)
        )
        # Map roles to LLM expected format
        llm_role = "assistant" if role == "assistant" else "user"
        conversation.append({"role": llm_role, "content": content})

    # Enrich current message with image description if available
    if image_description:
        enriched_message = f"""{user_message}

[El usuario envió una imagen. Descripción de la imagen:]
{image_description}

Responde al usuario basándote en la imagen que envió."""
        logger.info("Chat node: enriching message with image description")
    else:
        enriched_message = user_message

    # Add current message
    conversation.append({"role": "user", "content": enriched_message})

    logger.info(f"Chat node: processing with {len(conversation)-1} messages in history")

    # Use ainvoke for async consistency
    response = await llm.ainvoke(conversation)
    logger.info(f"Chat response: {response.content[:100]}")

    return {
        "messages": [{"role": "assistant", "content": response.content}],
        "next_action": "end"
    }
