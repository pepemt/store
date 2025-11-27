"""
WebSocket routes for real-time chat with the AI assistant.
Handles chat sessions, message streaming, and context management.
"""
import logging
import json
import sys
import os
import base64
from typing import Optional, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

# Image validation constants
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}

# Add agents directory to path
agents_path = os.path.join(os.path.dirname(__file__), 'agents')
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

from graph import build_graph
from chat_session import get_session_manager
from models import AgentState
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
    """Get or create the agent graph instance."""
    global _agent_graph
    if _agent_graph is None:
        try:
            _agent_graph = build_graph()
            logger.info("Agent graph initialized successfully")
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


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time chat.

    Query Parameters:
    - session_id: Optional existing session ID to resume conversation
    - customer_id: Optional customer ID for personalized responses
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
        await manager.send_message(session_id, {
            "type": "connection",
            "session_id": session_id,
            "message": "Conectado al asistente de La Tiendita de la Esquina",
            "history": chat_session.get_message_history(limit=10)
        })

        # Listen for messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                # Extraer conversation_id del cliente (puede ser None)
                conversation_id = message_data.get("conversation_id")

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
                            "conversation_id": conversation_id
                        })
                        continue

                    image_data = clean_base64
                    logger.info(f"Image received: {image_mime_type}, size ~{len(clean_base64) * 3 // 4 // 1024}KB")

                # Require either message or image
                if not user_message and not image_data:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Envía un mensaje o una imagen",
                        "conversation_id": conversation_id
                    })
                    continue

                # Add user message to session history (include [imagen] marker if image)
                session_message = user_message if user_message else ""
                if image_data:
                    session_message = f"[imagen adjunta] {session_message}".strip()
                chat_session.add_message("user", session_message)

                # Send typing indicator
                await manager.send_message(session_id, {
                    "type": "typing",
                    "message": "Escribiendo...",
                    "conversation_id": conversation_id  # Incluir conversation_id para typing
                })

                # Prepare agent state
                # Convert session messages to agent format
                agent_messages = []
                for msg in chat_session.get_message_history():
                    agent_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

                # Create initial state with image support
                initial_state: AgentState = {
                    "messages": agent_messages,
                    "intent": "",
                    "next_action": "",
                    "customer_id": chat_session.customer_id,
                    "search_query": None,
                    "category_filter": None,
                    "department_filter": None,
                    "products_found": [],
                    "conversation_context": chat_session.context,
                    # Image fields
                    "image_data": image_data,
                    "image_mime_type": image_mime_type if image_data else None,
                    "image_description": None,
                    "has_image": image_data is not None,
                }

                # Run agent graph with ainvoke (async)
                log_msg = f"Processing message for session {session_id}: {user_message or '(no text)'}"
                if image_data:
                    log_msg += " [with image]"
                logger.info(log_msg)
                result = await agent_graph.ainvoke(initial_state)

                # Extract response
                assistant_message = result["messages"][-1].content if result.get("messages") else "Lo siento, no pude procesar tu mensaje."
                products = result.get("products_found", [])
                intent = result.get("intent", "unknown")

                # Add assistant message to session
                chat_session.add_message("assistant", assistant_message)

                # Update session context - include image description if present
                context_update = {
                    "last_intent": intent,
                    "last_products": products[:3] if products else []  # Store up to 3 products
                }

                # Save image description for future reference in conversation
                if result.get("image_description"):
                    context_update["last_image_description"] = result.get("image_description")
                    logger.info(f"Saved image description to session context for future reference")

                chat_session.update_context(context_update)

                # Send response to client
                response_data = {
                    "type": "message",
                    "message": assistant_message,
                    "intent": intent,
                    "session_id": session_id,
                    "conversation_id": conversation_id  # Devolver conversation_id original
                }

                # Include products if found
                if products:
                    response_data["products"] = products

                await manager.send_message(session_id, response_data)

                logger.info(f"Response sent for session {session_id}")

            except json.JSONDecodeError:
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": "Formato de mensaje inválido",
                    "conversation_id": None  # No podemos extraer conversation_id si el JSON es inválido
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": "Error procesando el mensaje",
                    "conversation_id": conversation_id if 'conversation_id' in locals() else None
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
