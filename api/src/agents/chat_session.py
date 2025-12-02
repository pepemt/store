"""
Chat session management for maintaining conversation context.
Handles session storage, message history, and customer context.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ChatSession:
    """Represents a single chat session with history and context per conversation."""

    def __init__(self, session_id: str, customer_id: Optional[str] = None):
        self.session_id = session_id
        self.customer_id = customer_id
        # Almacenamiento por conversation_id
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}  # conversation_id -> messages
        self.conversation_contexts: Dict[str, Dict[str, Any]] = {}  # conversation_id -> context
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

    def add_message(self, role: str, content: str, conversation_id: str):
        """Add a message to a specific conversation."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
            self.conversation_contexts[conversation_id] = {}

        self.conversations[conversation_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.last_activity = datetime.utcnow()

    def update_context(self, updates: Dict[str, Any], conversation_id: str):
        """Update context for a specific conversation."""
        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = {}
        self.conversation_contexts[conversation_id].update(updates)
        self.last_activity = datetime.utcnow()

    def get_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get context for a specific conversation."""
        return self.conversation_contexts.get(conversation_id, {})

    def get_message_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages for a specific conversation, optionally limited to recent messages."""
        messages = self.conversations.get(conversation_id, [])
        if limit:
            return messages[-limit:]
        return messages

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "conversations": self.conversations,
            "conversation_contexts": self.conversation_contexts,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class ChatSessionManager:
    """
    Manages multiple chat sessions.
    Stores sessions in memory (can be extended to use Redis or database).
    """

    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        logger.info("ChatSessionManager initialized")

    def create_session(self, customer_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        session = ChatSession(session_id, customer_id)
        self.sessions[session_id] = session
        logger.info(f"Created new session: {session_id} for customer: {customer_id}")
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing session by ID."""
        return self.sessions.get(session_id)

    def get_or_create_session(self, session_id: Optional[str] = None, customer_id: Optional[str] = None) -> ChatSession:
        """Get existing session or create new one."""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            logger.info(f"Retrieved existing session: {session_id}")
            return session

        return self.create_session(customer_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        now = datetime.utcnow()
        to_delete = []

        for session_id, session in self.sessions.items():
            age = (now - session.last_activity).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(session_id)

        for session_id in to_delete:
            self.delete_session(session_id)

        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old sessions")

    def get_session_count(self) -> int:
        """Get total number of active sessions."""
        return len(self.sessions)


# Global session manager instance
_session_manager: Optional[ChatSessionManager] = None


def get_session_manager() -> ChatSessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = ChatSessionManager()
    return _session_manager
