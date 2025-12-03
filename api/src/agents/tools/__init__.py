"""
Generic tools for the intelligent orchestrator.

This package contains flexible, generic tools that the orchestrator can use
to handle any type of request dynamically.

NOTE: Due to naming conflict with the existing tools.py module,
imports should be done directly from the submodules:

    from tools.budget import BudgetHandler, parse_budget
    from tools.search import GenericSearchTool, search_products
    from tools.analyze import ContextualAnalyzer, ProductComparator
"""

# Lazy imports to avoid circular dependency with tools.py
# Don't import anything at module level - let consumers import directly

__all__ = [
    "budget",
    "search",
    "analyze",
]
