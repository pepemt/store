"""State definitions and type annotations for the conversational agent (LangGraph)"""

from __future__ import annotations

from typing import Annotated, Optional, List, Dict, Any, Literal, Callable, Awaitable
from typing_extensions import TypedDict, NotRequired
from langgraph.graph.message import add_messages
from dataclasses import dataclass, field
from enum import Enum


# -----------------------------
# Eventos de progreso (Thinking Steps)
# -----------------------------

class StepStatus(str, Enum):
    """Estado de un paso de procesamiento"""
    STARTED = "started"
    COMPLETED = "completed"
    ERROR = "error"


class StepType(str, Enum):
    """Tipos de pasos en el procesamiento"""
    ROUTING = "routing"           # Decisión de ruta (imagen/no imagen)
    VISION = "vision"             # Análisis de imagen
    CLASSIFIER = "classifier"     # Clasificación de intención
    CHAT = "chat"                 # Generación de respuesta conversacional
    SEARCH_REFINE = "search_refine"         # Refinamiento de query con LLM
    SEARCH_V1 = "search_v1"       # Búsqueda V1 (term-by-term)
    SEARCH_V2 = "search_v2"       # Búsqueda V2 (full query)
    SEARCH_V3 = "search_v3"       # Búsqueda V3 (distinctive)
    SEARCH_PARALLEL = "search_parallel"     # Búsquedas en paralelo
    DISCRIMINATOR = "discriminator"         # LLM discriminador
    RESPONSE_GEN = "response_gen"           # Generación de respuesta final
    REVIEW_SEARCH = "review_search"         # Búsqueda por reviews


@dataclass
class ThinkingStep:
    """Representa un paso en el proceso de pensamiento del agente"""
    step_type: StepType
    status: StepStatus
    title: str                              # Título corto para UI
    description: str                        # Descripción detallada
    details: Optional[Dict[str, Any]] = None  # Datos adicionales (ej: términos de búsqueda)
    is_parallel: bool = False               # Si es parte de operaciones paralelas
    parallel_group: Optional[str] = None    # ID del grupo paralelo (ej: "search_hybrid")
    duration_ms: Optional[int] = None       # Duración en ms (para completed)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para enviar por WebSocket"""
        return {
            "step_type": self.step_type.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "is_parallel": self.is_parallel,
            "parallel_group": self.parallel_group,
            "duration_ms": self.duration_ms,
        }


# Tipo para callback de eventos de progreso
ProgressCallback = Callable[[ThinkingStep], Awaitable[None]]


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
    "semantic_review_search",
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

    # Soporte de imágenes (visión)
    image_data: NotRequired[Optional[str]]           # base64 de la imagen (sin prefijo data:)
    image_mime_type: NotRequired[Optional[str]]      # "image/png" o "image/jpeg"
    image_description: NotRequired[Optional[str]]    # Descripción generada por vision_node
    has_image: NotRequired[bool]                     # Flag para routing condicional

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

    # Callback para eventos de progreso (thinking steps)
    progress_callback: NotRequired[Optional[ProgressCallback]]
