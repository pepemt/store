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
    user_message = state["messages"][-1].content

    # Get metadata cache for context
    metadata_cache = get_metadata_cache()
    metadata_context = metadata_cache.get_formatted_context()

    prompt = f"""Classify the user message into exactly ONE category. Respond with only the category name.

We sell these products:
{metadata_context}

Categories:
- product_search: User is looking for SPECIFIC products by name, color, type, or characteristics
  Examples: "busco pantalón negro", "show me blue shirts", "do you have jackets?", "necesito zapatos rojos"

- product_recommendations: User wants GENERAL suggestions or doesn't know what they want
  Examples: "what do you recommend?", "qué me sugieres?", "I need gift ideas", "show me popular items"

- chat: Greetings, questions about the store, policies, or general conversation
  Examples: "hello", "hola", "what's your return policy?", "how are you?"

IMPORTANT:
- If the user mentions a specific product type (shirt, pants, shoes, jacket) → product_search
- If the user mentions color, size, or specific features → product_search
- If the user just asks for suggestions without specifics → product_recommendations
- Greetings and store questions → chat

Now classify this message:
Message: {user_message}
Category:"""

    # Use ainvoke for async consistency
    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    intent = response.content.strip().lower()

    valid_intents = ["product_search", "product_recommendations", "chat"]
    if intent not in valid_intents:
        intent = "chat"

    logger.info(f"Classified intent: {intent}")
    return {"intent": intent}
