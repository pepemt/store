"""
Unified state definitions for the intelligent orchestrator architecture.

This module defines the state schema for the new unified agent architecture
that uses a single orchestrator to handle all request types dynamically.
"""

from __future__ import annotations

from typing import Annotated, Optional, List, Dict, Any, Literal, Callable, Awaitable
from typing_extensions import TypedDict, NotRequired
from langgraph.graph.message import add_messages
from dataclasses import dataclass, field
from enum import Enum


# -----------------------------
# Execution Plan Types
# -----------------------------

class ExecutionStep(TypedDict):
    """A single step in the orchestrator's execution plan."""
    id: str                          # Unique step identifier (e.g., "step_1")
    tool: str                        # Tool to use: "search", "analyze", "compare", "action"
    operation: str                   # Specific operation within the tool
    params: Dict[str, Any]           # Generic parameters for the tool
    depends_on: List[str]            # IDs of steps this depends on


class ExecutionPlan(TypedDict):
    """The orchestrator's execution plan."""
    reasoning: str                   # Brief explanation of the orchestrator's understanding
    steps: List[ExecutionStep]       # Steps to execute
    parallel_groups: List[List[str]] # Groups of step IDs that can run in parallel
    may_need_refinement: NotRequired[bool]  # If the plan may need refinement after execution


# -----------------------------
# Budget Types
# -----------------------------

class BudgetContext(TypedDict):
    """Budget information parsed from user request."""
    amount: float                    # Original amount in user's currency
    currency: str                    # Original currency code (USD, MXN, EUR, etc.)
    amount_usd: float                # Normalized amount in USD
    is_total: bool                   # True = total budget, False = per-item
    flexibility: float               # 0.0-1.0, how strict (0.1 = 10% over OK)


# -----------------------------
# Image Analysis Types
# -----------------------------

class ImageData(TypedDict):
    """Raw image data."""
    id: str                          # Unique image identifier
    data: str                        # Base64 encoded image data
    mime_type: str                   # MIME type (image/png, image/jpeg)


class ImageAnalysis(TypedDict):
    """Contextual analysis result for an image."""
    image_id: str                    # Reference to the source image
    analysis_type: str               # Type: "single_item", "multiple_items", "outfit", "comparison", "attributes"
    extracted_items: List[Dict[str, Any]]  # Items found in the image
    attributes: Dict[str, Any]       # Extracted attributes (color, style, etc.)
    search_queries: List[str]        # Generated search queries
    outfit_suggestions: NotRequired[List[Dict[str, Any]]]  # Outfit suggestions if applicable
    component_queries: NotRequired[Dict[str, List[str]]]  # Queries by component: {"top": [...], "bottom": [...]}


# -----------------------------
# Step Result Types (for multi-agent display)
# -----------------------------

class StepResult(TypedDict):
    """Result of a single step in a multi-agent task."""
    id: str                          # Step identifier ("step_1", "step_2", etc.)
    title: str                       # Display title ("Análisis de imagen", "Búsqueda: tops", etc.)
    description: str                 # Description of what was done
    status: str                      # "completed", "error", "skipped"
    products: NotRequired[List[Dict[str, Any]]]  # Products if this step found products
    analysis: NotRequired[Dict[str, Any]]        # Analysis result if applicable
    error: NotRequired[str]          # Error message if status is "error"


# -----------------------------
# Comparison Types
# -----------------------------

class ComparisonResult(TypedDict):
    """Result of comparing N products on M criteria."""
    products: List[Dict[str, Any]]   # Products being compared
    criteria: List[str]              # Criteria used for comparison
    matrix: Dict[str, Dict[str, Any]]  # Comparison matrix [criterion][product_id]
    insights: Dict[str, Any]         # Generated insights
    markdown_table: str              # Pre-formatted markdown table
    recommendation: NotRequired[str] # Best product for user's needs


# -----------------------------
# Variant Response Types (for Frontend)
# -----------------------------

class VariantSection(TypedDict):
    """A collapsible section in the frontend for variant responses."""
    id: str                          # Unique variant identifier
    title: str                       # LLM-generated title (e.g., "Persona 1 - Mujer con vestido azul")
    summary: str                     # Brief summary of this variant
    content: Dict[str, Any]          # Variant-specific content (products, outfit, budget)
    is_expanded: bool                # Should be expanded by default


class BudgetSummary(TypedDict):
    """Budget summary for multi-variant responses."""
    per_variant: List[float]         # Cost per variant
    total: float                     # Total cost
    currency: str                    # Currency code
    markdown_table: str              # Pre-formatted markdown table


class StructuredResponse(TypedDict):
    """Structured response for the frontend."""
    type: str                        # "single", "variants", "comparison", "multi_step"
    main_message: str                # Main message (general summary)

    # Only if type == "variants"
    variants: NotRequired[Optional[List[VariantSection]]]

    # Only if type == "comparison"
    comparison_table: NotRequired[Optional[str]]

    # Related products (if applicable)
    products: NotRequired[Optional[List[Dict[str, Any]]]]

    # Total budget (if applicable)
    budget_summary: NotRequired[Optional[BudgetSummary]]

    # Multi-step task results (collapsible display)
    step_results: NotRequired[Optional[List[StepResult]]]

    # Outfit components (for outfit requests)
    outfit_components: NotRequired[Optional[Dict[str, List[Dict[str, Any]]]]]


# -----------------------------
# Product Types (from existing)
# -----------------------------

class ProductDict(TypedDict):
    """Normalized product (shape returned by API and consumed by frontend)."""
    id: int
    name: str
    description: NotRequired[Optional[str]]
    category: NotRequired[Optional[str]]
    department: NotRequired[Optional[str]]
    price: NotRequired[float]
    stock: NotRequired[int]
    images: NotRequired[List[str]]
    rating: NotRequired[float]
    color_group: NotRequired[Optional[str]]
    product_type: NotRequired[Optional[str]]
    product_group: NotRequired[Optional[str]]


# -----------------------------
# Progress Callback Types (from existing)
# -----------------------------

class StepStatus(str, Enum):
    """Processing step status."""
    STARTED = "started"
    COMPLETED = "completed"
    ERROR = "error"


class StepType(str, Enum):
    """Types of processing steps."""
    ROUTING = "routing"
    VISION = "vision"
    CLASSIFIER = "classifier"
    CHAT = "chat"
    SEARCH_REFINE = "search_refine"
    SEARCH_V1 = "search_v1"
    SEARCH_V2 = "search_v2"
    SEARCH_V3 = "search_v3"
    SEARCH_PARALLEL = "search_parallel"
    DISCRIMINATOR = "discriminator"
    RESPONSE_GEN = "response_gen"
    REVIEW_SEARCH = "review_search"
    # New step types for orchestrator
    ORCHESTRATOR = "orchestrator"
    EXECUTOR = "executor"
    ANALYZE = "analyze"
    COMPARE = "compare"
    BUDGET = "budget"


@dataclass
class ThinkingStep:
    """Represents a step in the agent's thinking process."""
    step_type: StepType
    status: StepStatus
    title: str
    description: str
    details: Optional[Dict[str, Any]] = None
    is_parallel: bool = False
    parallel_group: Optional[str] = None
    duration_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for WebSocket transmission."""
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


# Callback type for progress events
ProgressCallback = Callable[[ThinkingStep], Awaitable[None]]


# -----------------------------
# Search Result Types
# -----------------------------

class SearchResult(TypedDict):
    """Result from the unified search tool."""
    products: List[ProductDict]
    strategies_used: List[str]       # Which search strategies were used
    search_method: NotRequired[str]  # Search method: "hybrid", "keyword", "filters", etc.
    budget_applied: NotRequired[Optional[float]]  # Budget filter if applied
    total_found: NotRequired[int]    # Total products found before limiting
    # Detailed breakdown for traceability
    v1_count: NotRequired[int]       # Products from V1 term-by-term search
    v2_count: NotRequired[int]       # Products from V2 full query search
    v3_count: NotRequired[int]       # Products from V3 distinctive terms (PRIORITY)
    distinctive_terms: NotRequired[List[str]]  # Distinctive terms found (e.g., ['unicorn', 'heart'])
    # Timing metrics (for progress events)
    refine_time_ms: NotRequired[int]           # Time spent refining query with LLM
    search_time_ms: NotRequired[int]           # Time spent in V1+V2+V3 parallel search
    discrimination_time_ms: NotRequired[int]   # Time spent in LLM discriminator


# -----------------------------
# Unified Agent State
# -----------------------------

class UnifiedAgentState(TypedDict):
    """
    Unified state for the intelligent orchestrator architecture.

    This state flows through the simplified graph:
    START -> orchestrator -> executor -> (refine?) -> response_generator -> END
    """
    # Conversation history (LangGraph concatenates with add_messages)
    messages: Annotated[list, add_messages]
    conversation_context: NotRequired[Dict[str, Any]]

    # User intent (interpreted, not classified)
    user_intent_summary: NotRequired[str]
    execution_plan: NotRequired[Optional[ExecutionPlan]]

    # Images (unified, contextual)
    images: NotRequired[List[ImageData]]
    image_analyses: NotRequired[List[ImageAnalysis]]

    # For backward compatibility with existing vision node
    image_data: NotRequired[Optional[str]]
    image_mime_type: NotRequired[Optional[str]]
    image_description: NotRequired[Optional[str]]
    has_image: NotRequired[bool]

    # Budget
    budget: NotRequired[Optional[BudgetContext]]

    # Search results
    search_results: NotRequired[Dict[str, SearchResult]]

    # Comparison results
    comparison_results: NotRequired[Optional[ComparisonResult]]

    # Accumulated products
    products_found: NotRequired[List[ProductDict]]
    products_pool: NotRequired[List[ProductDict]]
    previous_products: NotRequired[List[ProductDict]]  # Products from previous turn (for comparisons)

    # Execution tracking
    execution_results: NotRequired[Dict[str, Any]]
    iteration: NotRequired[int]
    max_iterations: NotRequired[int]

    # Structured response for frontend
    structured_response: NotRequired[Optional[StructuredResponse]]

    # E-commerce context (from existing)
    customer_id: NotRequired[Optional[str]]
    search_query: NotRequired[Optional[str]]
    category_filter: NotRequired[Optional[str]]
    department_filter: NotRequired[Optional[str]]
    selected_product: NotRequired[Optional[ProductDict]]

    # Progress callback
    progress_callback: NotRequired[Optional[ProgressCallback]]

    # Final response text
    response: NotRequired[str]


# -----------------------------
# Legacy State Alias (for backward compatibility)
# -----------------------------

# Alias for backward compatibility with existing code
AgentState = UnifiedAgentState
