"""Graph construction and compilation"""

from langgraph.graph import StateGraph, START, END
from models import AgentState
from nodes import (
    classifier_node,
    product_search_node,
    product_recommendations_node,
    chat_node,
)
from routing import route_by_intent


def build_graph():
    """Build graph with e-commerce routes"""
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("classifier", classifier_node)
    builder.add_node("product_search", product_search_node)
    builder.add_node("product_recommendations", product_recommendations_node)
    builder.add_node("chat", chat_node)

    # Flow
    builder.add_edge(START, "classifier")
    builder.add_conditional_edges(
        "classifier",
        route_by_intent,
        {
            "product_search": "product_search",
            "product_recommendations": "product_recommendations",
            "chat": "chat",
        }
    )
    builder.add_edge("product_search", END)
    builder.add_edge("product_recommendations", END)
    builder.add_edge("chat", END)

    return builder.compile()
