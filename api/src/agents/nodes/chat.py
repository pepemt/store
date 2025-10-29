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
    user_message = state["messages"][-1].content

    # Build context-aware system prompt
    system_prompt = """Eres un asistente amigable de La Tiendita de la Esquina, una tienda de ropa en línea.

Tu rol es:
- Saludar y ayudar a los clientes de manera amable
- Responder preguntas generales sobre la tienda
- Guiar a los clientes hacia la búsqueda de productos o recomendaciones
- Ser breve y conversacional

Si el cliente te pregunta sobre productos específicos o quiere recomendaciones, sugiéreles que te digan qué están buscando.

Responde de manera natural y amigable."""

    # Create conversation with context
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    # Use ainvoke for async consistency
    response = await llm.ainvoke(conversation)
    logger.info(f"Chat response: {response.content[:100]}")

    return {
        "messages": [{"role": "assistant", "content": response.content}],
        "next_action": "end"
    }
