"""State definitions and type annotations"""
from typing import Annotated, Optional, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State that flows through the graph"""
    messages: Annotated[list, add_messages]
    intent: str
    next_action: str
    # New fields for e-commerce context
    customer_id: Optional[str]  # Customer ID if authenticated
    search_query: Optional[str]  # Current search query
    category_filter: Optional[str]  # Category filter
    department_filter: Optional[str]  # Department filter
    products_found: List[Dict[str, Any]]  # Products found in search
    conversation_context: Dict[str, Any]  # Additional context for conversation
