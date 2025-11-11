"""Graph construction and compilation"""

from langgraph.graph import StateGraph, START, END
from models import AgentState
from nodes import semantic_product_search_node


def build_graph():
    """Build graph with ONLY semantic product search"""
    builder = StateGraph(AgentState)

    # Add only semantic search node
    builder.add_node("semantic_search", semantic_product_search_node)

    # Direct flow: START -> semantic_search -> END
    builder.add_edge(START, "semantic_search")
    builder.add_edge("semantic_search", END)

    return builder.compile()
