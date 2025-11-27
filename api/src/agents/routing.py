"""Routing logic for the agent graph"""
import logging
from typing import Literal
from models import AgentState

logger = logging.getLogger(__name__)


def route_by_image(state: AgentState) -> Literal["has_image", "no_image"]:
    """Route based on whether the message contains an image"""
    has_image = state.get("has_image", False) or state.get("image_data") is not None
    result = "has_image" if has_image else "no_image"
    logger.debug(f"Image routing: {result}")
    return result


def route_by_intent(state: AgentState) -> Literal["product_search", "product_recommendations", "chat"]:
    """Route to appropriate handler based on intent"""
    intent = state.get("intent", "chat")
    logger.debug(f"Routing to: {intent}")
    return intent
