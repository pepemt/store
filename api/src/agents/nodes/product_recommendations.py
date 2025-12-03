"""Product recommendations node"""
import logging
import sys
import os
import importlib.util

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _parent_dir)

from models import AgentState
from llm_config import llm

# Import from tools.py (file) using importlib to avoid conflict with tools/ directory
_tools_py_path = os.path.join(_parent_dir, "tools.py")
_tools_spec = importlib.util.spec_from_file_location("tools_module", _tools_py_path)
_tools_module = importlib.util.module_from_spec(_tools_spec)
_tools_spec.loader.exec_module(_tools_module)
get_product_recommendations = _tools_module.get_product_recommendations

logger = logging.getLogger(__name__)


async def product_recommendations_node(state: AgentState) -> dict:
    """
    Provide product recommendations.
    Can be personalized if customer_id is provided.
    """
    user_message = state["messages"][-1].content
    customer_id = state.get("customer_id")

    try:
        # Get recommendations - simple await
        products = await get_product_recommendations(customer_id=customer_id, limit=5)

        # Format response
        if products:
            products_text = "\n".join([
                f"- {p['name']} (${p['price']:.2f}) - {p['category']}"
                for p in products
            ])

            if customer_id:
                response_prompt = f"""You are a helpful shopping assistant. The user asked: "{user_message}"

Based on their purchase history, I recommend these products:
{products_text}

Provide a friendly, personalized response presenting these recommendations.
Explain that these are based on their previous purchases."""
            else:
                response_prompt = f"""You are a helpful shopping assistant. The user asked: "{user_message}"

Here are our popular products:
{products_text}

Provide a friendly response presenting these recommendations.
Mention that these are popular items."""

            response = await llm.ainvoke([{"role": "user", "content": response_prompt}])
            response_content = response.content
        else:
            response_content = "Lo siento, no pude obtener recomendaciones en este momento. ¿Hay algo específico que estés buscando?"

        logger.info(f"Recommendations completed: {len(products)} products")

        return {
            "messages": [{"role": "assistant", "content": response_content}],
            "products_found": products,
            "next_action": "end"
        }

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return {
            "messages": [{"role": "assistant", "content": "Disculpa, tuve un problema obteniendo recomendaciones."}],
            "products_found": [],
            "next_action": "end"
        }
