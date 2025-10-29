"""Routing logic for the agent graph"""
import logging
from typing import Literal
from models import AgentState

logger = logging.getLogger(__name__)


def route_by_intent(state: AgentState) -> Literal["product_search", "product_recommendations", "chat"]:
    """Route to appropriate handler based on intent"""
    intent = state.get("intent", "chat")
    logger.debug(f"Routing to: {intent}")
    return intent
