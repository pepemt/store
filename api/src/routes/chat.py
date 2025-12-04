"""
WebSocket routes for real-time chat with the AI assistant.
Handles chat sessions, message streaming, and context management.
"""
import logging
import json
import sys
import os
import base64
from typing import Optional, Tuple, Callable, Awaitable
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

# Image validation constants
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}

# Add agents directory to path
agents_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents')
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

from graph import build_graph
from chat_session import get_session_manager
from models import ThinkingStep
from state import UnifiedAgentState
from metadata_cache import get_metadata_cache

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy initialization of agent graph and session manager
_agent_graph = None
_session_manager = None
_metadata_initialized = False


async def initialize_metadata():
    """Initialize metadata cache."""
    global _metadata_initialized
    if not _metadata_initialized:
        try:
            metadata_cache = get_metadata_cache()
            await metadata_cache.refresh(force=True)
            logger.info("Metadata cache initialized successfully")
            _metadata_initialized = True
        except Exception as e:
            logger.error(f"Error initializing metadata cache: {e}", exc_info=True)


def get_agent_graph():
    """Get or create the unified orchestrator graph instance."""
    global _agent_graph
    if _agent_graph is None:
        try:
            _agent_graph = build_graph()
            logger.info("Agent graph initialized: ORCHESTRATOR")
        except Exception as e:
            logger.error(f"Error building agent graph: {e}", exc_info=True)
            raise
    return _agent_graph


def get_session_manager_instance():
    """Get or create the session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = get_session_manager()
    return _session_manager


class ChatMessage(BaseModel):
    """Chat message model."""
    message: str = ""  # Optional if image is provided
    image: Optional[str] = None  # Base64 encoded image
    image_mime_type: Optional[str] = None  # "image/png" or "image/jpeg"
    session_id: Optional[str] = None
    customer_id: Optional[str] = None
    conversation_id: Optional[str] = None  # Frontend conversation ID


def validate_image(image_base64: str, mime_type: Optional[str]) -> Tuple[bool, str, str]:
    """
    Validate image size and type.
    Returns (is_valid, error_message, clean_base64)
    """
    if not mime_type:
        mime_type = "image/jpeg"  # Default assumption

    if mime_type not in ALLOWED_MIME_TYPES:
        return False, "Tipo de imagen no soportado. Usa PNG o JPG.", ""

    try:
        # Remove data URL prefix if present
        clean_base64 = image_base64
        if "base64," in image_base64:
            clean_base64 = image_base64.split("base64,")[1]

        # Validate base64 and check size
        decoded = base64.b64decode(clean_base64)
        if len(decoded) > MAX_IMAGE_SIZE_BYTES:
            return False, f"Imagen muy grande. Máximo {MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB.", ""

        return True, "", clean_base64
    except Exception as e:
        logger.error(f"Image validation error: {e}")
        return False, "Formato de imagen inválido.", ""


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """Send a message to a specific WebSocket."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)


manager = ConnectionManager()


def create_progress_callback(
    session_id: str,
    conversation_id: str,
    connection_manager: ConnectionManager
) -> Callable[[ThinkingStep], Awaitable[None]]:
    """
    Crea un callback para enviar eventos de progreso por WebSocket.

    Args:
        session_id: ID de la sesión WebSocket
        conversation_id: ID de la conversación
        connection_manager: Manager de conexiones WebSocket

    Returns:
        Función async que recibe un ThinkingStep y lo envía por WebSocket
    """
    async def progress_callback(step: ThinkingStep) -> None:
        """Envía un evento de progreso por WebSocket."""
        try:
            await connection_manager.send_message(session_id, {
                "type": "thinking_step",
                "conversation_id": conversation_id,
                "step": step.to_dict()
            })
        except Exception as e:
            logger.warning(f"Error sending progress event: {e}")

    return progress_callback


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time chat.

    Query Parameters:
    - session_id: Optional existing session ID to resume conversation
    - customer_id: Optional customer ID for personalized responses
    - conversation_id: Optional conversation ID to load specific conversation history
    """
    try:
        # Initialize metadata cache first
        await initialize_metadata()

        # Initialize components
        agent_graph = get_agent_graph()
        session_manager = get_session_manager_instance()
    except Exception as e:
        logger.error(f"Failed to initialize chat components: {e}")
        await websocket.close(code=1011, reason="Service initialization failed")
        return

    # Get or create session
    chat_session = session_manager.get_or_create_session(session_id, customer_id)
    session_id = chat_session.session_id

    # Connect WebSocket
    await manager.connect(websocket, session_id)

    try:
        # Send welcome message with session info
        # Solo enviar historial si se especifica conversation_id
        history = chat_session.get_message_history(conversation_id, limit=10) if conversation_id else []
        await manager.send_message(session_id, {
            "type": "connection",
            "session_id": session_id,
            "message": "Conectado al asistente de Zenith",
            "history": history
        })

        # Listen for messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                # Extraer conversation_id del cliente con fallback
                msg_conversation_id = message_data.get("conversation_id")
                if not msg_conversation_id:
                    msg_conversation_id = f"default_{session_id}"  # Fallback para compatibilidad

                # Extract and validate image if present
                image_data = None
                image_mime_type = None
                raw_image = message_data.get("image")

                if raw_image:
                    image_mime_type = message_data.get("image_mime_type", "image/jpeg")
                    is_valid, error_msg, clean_base64 = validate_image(raw_image, image_mime_type)

                    if not is_valid:
                        await manager.send_message(session_id, {
                            "type": "error",
                            "message": error_msg,
                            "conversation_id": msg_conversation_id
                        })
                        continue

                    image_data = clean_base64
                    logger.info(f"Image received: {image_mime_type}, size ~{len(clean_base64) * 3 // 4 // 1024}KB")

                # Require either message or image
                if not user_message and not image_data:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Envía un mensaje o una imagen",
                        "conversation_id": msg_conversation_id
                    })
                    continue

                # Add user message to session history (include [imagen] marker if image)
                session_message = user_message if user_message else ""
                if image_data:
                    session_message = f"[imagen adjunta] {session_message}".strip()
                chat_session.add_message("user", session_message, msg_conversation_id)

                # Send typing indicator
                await manager.send_message(session_id, {
                    "type": "typing",
                    "message": "Escribiendo...",
                    "conversation_id": msg_conversation_id
                })

                # Prepare agent state
                # Convert session messages to agent format (solo de esta conversación)
                agent_messages = []
                for msg in chat_session.get_message_history(msg_conversation_id):
                    agent_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

                # Create progress callback for this conversation
                progress_callback = create_progress_callback(
                    session_id=session_id,
                    conversation_id=msg_conversation_id,
                    connection_manager=manager
                )

                # Get conversation context with previous products
                conv_context = chat_session.get_context(msg_conversation_id)
                previous_products = conv_context.get("last_products", [])

                # Create initial state with image support
                # The state format works for both legacy and orchestrator graphs
                initial_state = {
                    "messages": agent_messages,
                    "intent": "",
                    "next_action": "",
                    "customer_id": chat_session.customer_id,
                    "search_query": None,
                    "category_filter": None,
                    "department_filter": None,
                    "products_found": [],
                    "conversation_context": conv_context,
                    "previous_products": previous_products,  # Products from previous turn
                    # Image fields
                    "image_data": image_data,
                    "image_mime_type": image_mime_type if image_data else None,
                    "image_description": None,
                    "has_image": image_data is not None,
                    # Progress callback for streaming events
                    "progress_callback": progress_callback,
                    # Orchestrator-specific fields
                    "execution_plan": None,
                    "execution_results": {},
                    "user_intent_summary": "",
                    "budget": None,
                    "iteration": 0,
                    "max_iterations": 5,
                    "structured_response": None,
                }

                # Run agent graph with ainvoke (async)
                log_msg = f"Processing message for session {session_id}: {user_message or '(no text)'}"
                if image_data:
                    log_msg += " [with image]"
                logger.info(log_msg)
                result = await agent_graph.ainvoke(initial_state)

                # Extract response - handle both legacy and orchestrator formats
                if result.get("response"):
                    # Orchestrator mode: response is in 'response' field
                    assistant_message = result["response"]
                elif result.get("messages"):
                    # Legacy mode: response is in messages
                    assistant_message = result["messages"][-1].content
                else:
                    assistant_message = "Lo siento, no pude procesar tu mensaje."

                products = result.get("products_found", [])
                intent = result.get("intent") or result.get("user_intent_summary", "unknown")

                # If image was analyzed, add interpretation to history as context
                if result.get("image_description"):
                    # Format that's clear for the LLM to understand and reference later
                    image_note = f"[IMAGEN ANALIZADA] El usuario envió una imagen. Contenido detectado: {result['image_description']}"
                    chat_session.add_message("system", image_note, msg_conversation_id)
                    logger.info(f"Added image analysis to conversation history: {result['image_description'][:100]}...")

                # Add assistant message to session
                chat_session.add_message("assistant", assistant_message, msg_conversation_id)

                # Update session context
                context_update = {
                    "last_intent": intent,
                    "last_products": products[:10] if products else []  # Store up to 10 products for comparisons
                }

                chat_session.update_context(context_update, msg_conversation_id)
                search_method = result.get("search_method")

                # Send response to client
                response_data = {
                    "type": "message",
                    "message": assistant_message,
                    "intent": intent,
                    "session_id": session_id,
                    "conversation_id": msg_conversation_id
                }
                if search_method:
                    response_data["search_method"] = search_method
                # Include products if found
                if products:
                    response_data["products"] = products

                # Include structured response if available (orchestrator mode)
                structured_response = result.get("structured_response")
                logger.info(f"structured_response available: {structured_response is not None}")
                if structured_response:
                    logger.info(f"structured_response keys: {list(structured_response.keys())}")
                    response_data["structured_response"] = structured_response
                    # If it has variants, mark the response type
                    if structured_response.get("type") == "variants":
                        response_data["has_variants"] = True
                        response_data["variants"] = structured_response.get("variants", [])
                    # If it has comparison table
                    if structured_response.get("comparison_table"):
                        logger.info(f"comparison_table found with recommendation: {structured_response['comparison_table'].get('recommendation', '')[:50]}...")
                        response_data["comparison_table"] = structured_response["comparison_table"]
                    # If it has budget summary
                    if structured_response.get("budget_summary"):
                        response_data["budget_summary"] = structured_response["budget_summary"]
                    # If it has step results (multi-step display)
                    if structured_response.get("step_results"):
                        logger.info(f"step_results count: {len(structured_response['step_results'])}")
                        for sr in structured_response["step_results"]:
                            logger.info(f"  - {sr.get('id')}: {sr.get('title')} - {len(sr.get('products', []))} productos")
                        response_data["step_results"] = structured_response["step_results"]
                    else:
                        logger.warning("No step_results in structured_response")
                    # If it has outfit components
                    if structured_response.get("outfit_components"):
                        response_data["outfit_components"] = structured_response["outfit_components"]
                else:
                    logger.warning("No structured_response in result")

                await manager.send_message(session_id, response_data)

                logger.info(f"Response sent for session {session_id}")

            except json.JSONDecodeError:
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": "Formato de mensaje inválido",
                    "conversation_id": None
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": "Error procesando el mensaje",
                    "conversation_id": msg_conversation_id if 'msg_conversation_id' in locals() else None
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(session_id)


@router.get("/health")
async def chat_health():
    """Check if chat service is ready."""
    try:
        session_manager = get_session_manager_instance()
        return {
            "status": "healthy",
            "message": "Chat service is ready",
            "active_sessions": session_manager.get_session_count()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/sessions/count")
async def get_active_sessions():
    """Get the number of active chat sessions."""
    session_manager = get_session_manager_instance()
    return {
        "active_sessions": session_manager.get_session_count()
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific chat session."""
    session_manager = get_session_manager_instance()
    deleted = session_manager.delete_session(session_id)
    if deleted:
        return {"message": "Session deleted successfully"}
    return {"message": "Session not found"}


@router.post("/sessions/cleanup")
async def cleanup_old_sessions(max_age_hours: int = 24):
    """Clean up old sessions."""
    session_manager = get_session_manager_instance()
    session_manager.cleanup_old_sessions(max_age_hours)
    return {
        "message": "Cleanup completed",
        "remaining_sessions": session_manager.get_session_count()
    }
