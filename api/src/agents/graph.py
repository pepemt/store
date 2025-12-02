"""Graph construction and compilation"""

from langgraph.graph import StateGraph, START, END
from models import AgentState
from nodes import (
    semantic_product_search_node,
    chat_node,
    classifier_node,
    vision_node,
    semantic_review_search_node
)
from routing import route_by_intent, route_by_image


def build_graph():
    """Build multi-agent graph with vision support, intent classification and routing"""
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("vision", vision_node)
    builder.add_node("classifier", classifier_node)
    builder.add_node("chat", chat_node)
    builder.add_node("product_search", semantic_product_search_node)
    builder.add_node("review_search", semantic_review_search_node)


    # Flow: START -> check if image exists
    # If image -> vision_node -> classifier
    # If no image -> classifier directly
    builder.add_conditional_edges(
        START,
        route_by_image,
        {
            "has_image": "vision",
            "no_image": "classifier"
        }
    )

    # Vision always goes to classifier after processing
    builder.add_edge("vision", "classifier")

    # Conditional routing based on intent
    # Both product_search and product_recommendations go to semantic search
    builder.add_conditional_edges(
        "classifier",
        route_by_intent,
        {
            "chat": "chat",
            "product_search": "product_search",
            "product_recommendations": "product_search",  # Recomendaciones también usan búsqueda semántica
            "semantic_review_search": "review_search"
        }
    )

    # All paths lead to END
    builder.add_edge("chat", END)
    builder.add_edge("product_search", END)
    builder.add_edge("review_search", END)


    return builder.compile()
