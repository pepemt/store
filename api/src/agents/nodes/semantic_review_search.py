"""Review-based semantic search node."""
import logging
import sys
import os

# Paths para imports locales y review_search en api/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))            # .../api/src/agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))  # .../api

from models import AgentState
from llm_config import llm
from review_search import ReviewSearchEngine

logger = logging.getLogger(__name__)
_engine: ReviewSearchEngine | None = None


def _get_engine() -> ReviewSearchEngine:
    global _engine
    if _engine is None:
        logger.info("Inicializando ReviewSearchEngine (reviews embeddings + FAISS)")
        _engine = ReviewSearchEngine()
    return _engine


async def semantic_review_search_node(state: AgentState) -> dict:
    """Busca productos por similitud de reviews en función de la necesidad del usuario."""
    messages = state["messages"]
    user_message = messages[-1].content if messages else ""
    engine = _get_engine()

    try:
        review_hits = engine.search_reviews(user_message, top_k=50)
        ranked = engine.aggregate_products(review_hits)
        products = await engine.get_products(ranked, limit=10)

        if products:
            items_text = "\n".join(
                f"- {p['name']} (${p['price']:.2f}) | {p.get('category','')} | "
                f"evidencia: \"{(p.get('evidence_review','')[:177] + '...') if p.get('evidence_review') and len(p.get('evidence_review'))>180 else p.get('evidence_review','')}\""
                for p in products[:5]
            )
            response_prompt = f"""Usuario: "{user_message}"
He buscado productos basándome en opiniones/reviews similares a esa necesidad.
Resultados (con la review más parecida como evidencia):
{items_text}

Responde en el mismo idioma que el usuario, menciona que las recomendaciones se basan en opiniones/reviews, y resalta 2-3 productos explicando por qué encajan según la evidencia mostrada."""
            response = await llm.ainvoke([{"role": "user", "content": response_prompt}])
            content = response.content
        else:
            content = "No encontré productos basados en opiniones para lo que buscas. ¿Puedes darme más detalle?"

        return {
            "messages": [{"role": "assistant", "content": content}],
            "products_found": products,
            "search_method": "semantic_reviews",
            "next_action": "end",
        }

    except Exception as e:
        logger.error(f"Error en semantic_review_search_node: {e}", exc_info=True)
        return {
            "messages": [{"role": "assistant", "content": "Disculpa, tuve un problema buscando por reviews. ¿Puedes intentar de nuevo?"}],
            "products_found": [],
            "next_action": "end",
        }
