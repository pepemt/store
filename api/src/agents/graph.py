"""
Unified orchestrator graph.

This module provides the main agent graph that handles all types of queries:
- Simple greetings and questions
- Product searches
- Image analysis
- Budget handling
- Complex outfit/comparison requests

The orchestrator dynamically decides what tools to use based on context.
"""

from langgraph.graph import StateGraph, START, END
from typing import Literal

from state import UnifiedAgentState
from orchestrator import (
    orchestrator_node,
    executor_node,
    response_generator_node,
    should_continue
)


def _should_continue_wrapper(state: UnifiedAgentState) -> Literal["refine", "generate"]:
    """Wrapper for should_continue to ensure correct return type."""
    result = should_continue(state)
    return "refine" if result == "refine" else "generate"


def build_graph():
    """
    Build the unified orchestrator graph.

    Architecture:
    START -> orchestrator -> executor -> (refine?) -> response_generator -> END

    The orchestrator:
    - Understands full context (text, images, budget, conversation)
    - Generates execution plans with dependency support
    - Adapts dynamically based on results

    Features:
    - Dynamic tool selection (search, analyze, compare, budget)
    - Parallel execution of independent operations
    - Budget handling with currency conversion
    - Contextual image analysis
    - N-product comparison
    - Variant responses for complex queries

    Returns:
        Compiled LangGraph StateGraph
    """
    builder = StateGraph(UnifiedAgentState)

    # Add nodes
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("executor", executor_node)
    builder.add_node("response_generator", response_generator_node)

    # Flow: START -> orchestrator
    builder.add_edge(START, "orchestrator")

    # Orchestrator -> executor
    builder.add_edge("orchestrator", "executor")

    # Executor -> conditional (refine or generate)
    builder.add_conditional_edges(
        "executor",
        _should_continue_wrapper,
        {
            "refine": "orchestrator",       # Loop back for refinement
            "generate": "response_generator"  # Generate final response
        }
    )

    # Response generator -> END
    builder.add_edge("response_generator", END)

    return builder.compile()


__all__ = ["build_graph"]
