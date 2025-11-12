"""Graph construction and compilation"""

from langgraph.graph import StateGraph, START, END
from models import AgentState
from nodes import (
    semantic_product_search_node,
    chat_node,
    classifier_node
)
from routing import route_by_intent


def build_graph():
    """Build multi-agent graph with intent classification and routing"""
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("classifier", classifier_node)
    builder.add_node("chat", chat_node)
    builder.add_node("product_search", semantic_product_search_node)

    # Flow: START -> classifier
    builder.add_edge(START, "classifier")

    # Conditional routing based on intent
    # Both product_search and product_recommendations go to semantic search
    builder.add_conditional_edges(
        "classifier",
        route_by_intent,
        {
            "chat": "chat",
            "product_search": "product_search",
            "product_recommendations": "product_search"  # Recomendaciones también usan búsqueda semántica
        }
    )

    # All paths lead to END
    builder.add_edge("chat", END)
    builder.add_edge("product_search", END)

    return builder.compile()
