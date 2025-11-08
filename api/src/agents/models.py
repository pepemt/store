"""State definitions and type annotations for the conversational agent (LangGraph)"""

from __future__ import annotations

from typing import Annotated, Optional, List, Dict, Any, Literal
from typing_extensions import TypedDict, NotRequired
from langgraph.graph.message import add_messages


# -----------------------------
# Tipos de dominio e-commerce
# -----------------------------

class ProductDict(TypedDict):
    """Producto normalizado (shape que devuelve la API y que consume el front)."""
    id: int
    name: str
    description: NotRequired[Optional[str]]
    category: NotRequired[Optional[str]]       # product_group_name recomendado
    department: NotRequired[Optional[str]]     # department_name
    price: NotRequired[float]                  # puede venir de tabla de precios o transacciones
    stock: NotRequired[int]
    images: NotRequired[List[str]]
    rating: NotRequired[float]
    # extras útiles
    color_group: NotRequired[Optional[str]]
    product_type: NotRequired[Optional[str]]
    product_group: NotRequired[Optional[str]]  # alias de category comercial


class CartItemDict(TypedDict):
    """Item de carrito simplificado para el agente."""
    id: int
    article_id: int
    quantity: int
    article_name: NotRequired[Optional[str]]
    article_price: NotRequired[Optional[float]]
    article_image: NotRequired[Optional[str]]


class CartSummaryDict(TypedDict):
    """Resumen de carrito para prompts/razonamiento del agente."""
    customer_id: str
    items: List[CartItemDict]
    total_items: int
    total_quantity: int
    total_amount: float


# -----------------------------
# Intents y acciones del agente
# -----------------------------

AgentIntent = Literal[
    "smalltalk",
    "search_products",
    "filter_products",
    "show_product",
    "add_to_cart",
    "remove_from_cart",
    "show_cart",
    "checkout",
    "unknown",
]

NextAction = Literal[
    "ask_clarifying_question",
    "call_products_api",
    "call_cart_api_add",
    "call_cart_api_remove",
    "call_cart_api_get",
    "render_product_list",
    "render_product_details",
    "render_cart",
    "handoff",
    "none",
]


# -----------------------------
# Estado del grafo conversacional
# -----------------------------

class AgentState(TypedDict):
    """Estado que fluye por el grafo de LangGraph."""
    # Historial de mensajes (LangGraph concatena con add_messages)
    messages: Annotated[list, add_messages]

    # Clasificación de intención y siguiente acción
    intent: AgentIntent
    next_action: NextAction

    # Contexto e-commerce
    customer_id: NotRequired[Optional[str]]          # ID del cliente si está autenticado
    search_query: NotRequired[Optional[str]]         # término de búsqueda actual
    category_filter: NotRequired[Optional[str]]      # filtro de categoría (product_group_name)
    department_filter: NotRequired[Optional[str]]    # filtro de departamento

    # Resultados/buffers de trabajo
    products_found: NotRequired[List[ProductDict]]   # resultados de búsqueda/listado
    selected_product: NotRequired[Optional[ProductDict]]  # producto focal si aplica

    # Carrito (cuando se use)
    cart: NotRequired[Optional[CartSummaryDict]]

    # Cualquier otro dato de contexto (flags, temporales, etc.)
    conversation_context: NotRequired[Dict[str, Any]]
