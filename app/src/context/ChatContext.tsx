import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react'

interface ChatMessage {
  id: number
  text: string
  sender: 'user' | 'assistant'
  timestamp: string
  products?: any[] | null
  intent?: string | null
}

interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}

interface ChatContextType {
  isOpen: boolean
  messages: ChatMessage[]
  isTyping: boolean
  isConnected: boolean
  sessionId: string | null
  conversations: Conversation[]
  activeConversationId: string | null
  addMessage: (message: Partial<ChatMessage>) => ChatMessage
  sendMessage: (text: string) => Promise<void>
  clearMessages: () => void
  toggleChat: () => void
  closeChat: () => void
  openChat: () => void
  createNewConversation: () => void
  deleteConversation: (id: string) => void
  switchConversation: (id: string) => void
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

const getWebSocketURL = (): string => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

  // En localhost, usar puerto explícito; en producción/Tailscale, usar el mismo host:port que la página
  if (isLocalhost) {
    const port = import.meta.env.VITE_API_PORT || '8000'
    return `${protocol}//localhost:${port}/api/v1/chat/ws/chat`
  }

  // En producción, usar window.location.host (incluye hostname y puerto si no es estándar)
  return `${protocol}//${window.location.host}/api/v1/chat/ws/chat`
}

const WS_URL = getWebSocketURL()

interface ChatProviderProps {
  children: ReactNode
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('tiendita_conversations') || '[]')
    } catch {
      return []
    }
  })
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    try {
      const saved = localStorage.getItem('tiendita_active_conversation_id')
      return saved || null
    } catch {
      return null
    }
  })
  // Rastrear qué conversación está esperando respuesta (typing)
  const [typingConversationId, setTypingConversationId] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)

  const messages = conversations.find(c => c.id === activeConversationId)?.messages || []

  // isTyping es true solo si la conversación ACTIVA está esperando respuesta
  const isTyping = typingConversationId === activeConversationId

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const customerIdRef = useRef<string | null>(null)
  const activeConversationIdRef = useRef<string | null>(activeConversationId)

  // Sync ref with state
  useEffect(() => {
    activeConversationIdRef.current = activeConversationId
  }, [activeConversationId])

  useEffect(() => {
    try {
      const user = JSON.parse(localStorage.getItem('tiendita_user') || 'null')
      if (user?.id) {
        customerIdRef.current = user.id
      }
    } catch (e) {
      console.error('Error obteniendo usuario:', e)
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('tiendita_conversations', JSON.stringify(conversations))
  }, [conversations])

  useEffect(() => {
    if (activeConversationId) {
      localStorage.setItem('tiendita_active_conversation_id', activeConversationId)
    } else {
      localStorage.removeItem('tiendita_active_conversation_id')
    }
  }, [activeConversationId])

  const addMessage = (
    message: Partial<ChatMessage>,
    targetConversationId?: string | null  // Parámetro opcional para conversación específica
  ): ChatMessage => {
    const newMessage: ChatMessage = {
      id: Date.now() + Math.random(),
      text: message.text || '',
      sender: message.sender || 'user',
      timestamp: new Date().toISOString(),
      products: message.products || null,
      intent: message.intent || null
    }

    let newConvId: string | null = null

    setConversations(prev => {
      // Si se especifica targetConversationId, usarlo; si no, usar el actual
      const targetId = targetConversationId !== undefined
        ? targetConversationId
        : activeConversationIdRef.current

      // Buscar conversación objetivo
      let targetConv = prev.find(c => c.id === targetId)

      // Si no hay conversación objetivo, usar la más reciente
      if (!targetConv && prev.length > 0) {
        targetConv = prev[0]
      }

      // Si encontramos una conversación objetivo, agregar mensaje
      if (targetConv) {
        // NO actualizar activeConversationId cuando viene de WebSocket
        // (solo cuando el usuario está agregando mensajes directamente)
        if (targetConversationId === undefined && targetId !== targetConv.id) {
          setActiveConversationId(targetConv.id)
        }

        return prev.map(conv =>
          conv.id === targetConv.id
            ? {
                ...conv,
                messages: [...conv.messages, newMessage],
                updatedAt: new Date().toISOString()
              }
            : conv
        )
      }

      // No hay conversaciones, crear una nueva
      newConvId = `conv_${Date.now()}`
      const title = message.sender === 'user' && message.text
        ? message.text.slice(0, 30)
        : 'Nueva conversación'

      const newConversation: Conversation = {
        id: newConvId,
        title: title,
        messages: [newMessage],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }

      setActiveConversationId(newConvId)
      return [newConversation]
    })

    return newMessage
  }

  const connectWebSocket = (): void => {
    try {
      let wsUrl = WS_URL
      const params: string[] = []

      if (sessionId) {
        params.push(`session_id=${encodeURIComponent(sessionId)}`)
      }
      if (customerIdRef.current) {
        params.push(`customer_id=${encodeURIComponent(customerIdRef.current)}`)
      }

      if (params.length > 0) {
        wsUrl += (wsUrl.includes('?') ? '&' : '?') + params.join('&')
      }

      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket conectado')
        setIsConnected(true)
        setTypingConversationId(null)  // Limpiar estado de typing al conectar
        reconnectAttemptsRef.current = 0

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('Mensaje recibido:', data)

          switch (data.type) {
            case 'connection':
              if (data.session_id) {
                setSessionId(data.session_id)
              }
              // El historial se carga desde localStorage, no del WebSocket
              break

            case 'typing':
              // Marcar que ESA conversación específica está esperando respuesta
              if (data.conversation_id) {
                setTypingConversationId(data.conversation_id)
              }
              break

            case 'message':
              // Si la respuesta es para la conversación que está typing, limpiar
              setTypingConversationId(prev =>
                prev === data.conversation_id ? null : prev
              )
              // Usar conversation_id del backend para colocar mensaje en conversación correcta
              addMessage({
                text: data.message,
                sender: 'assistant',
                products: data.products || null,
                intent: data.intent || null
              }, data.conversation_id)  // Backend devuelve el conversation_id original
              if (data.session_id) {
                setSessionId(data.session_id)
              }
              break

            case 'error':
              // Limpiar typing si el error es para esa conversación
              setTypingConversationId(prev =>
                prev === data.conversation_id ? null : prev
              )
              // También usar conversation_id para errores
              addMessage({
                text: data.message || 'Lo siento, hubo un error. Intenta nuevamente.',
                sender: 'assistant'
              }, data.conversation_id)
              break

            default:
              console.warn('Tipo de mensaje desconocido:', data.type)
          }
        } catch (error) {
          console.error('Error procesando mensaje WebSocket:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('Error en WebSocket:', error)
        setIsConnected(false)
      }

      ws.onclose = () => {
        console.log('WebSocket desconectado')
        setIsConnected(false)
        setTypingConversationId(null)  // Limpiar estado de typing al desconectar

        if (reconnectAttemptsRef.current < 5) {
          reconnectAttemptsRef.current++
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          console.log(`Reintentando conexión en ${delay}ms (intento ${reconnectAttemptsRef.current})`)

          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket()
          }, delay)
        } else {
          console.error('Máximo de intentos de reconexión alcanzado')
          addMessage({
            text: 'Error de conexión. Por favor, recarga la página.',
            sender: 'assistant'
          })
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Error conectando WebSocket:', error)
      setIsConnected(false)
    }
  }

  // Asegurar que siempre hay una conversación activa cuando el chat está abierto
  useEffect(() => {
    if (isOpen && conversations.length === 0) {
      // Si no hay conversaciones, crear una nueva
      const newConvId = `conv_${Date.now()}`
      const newConversation: Conversation = {
        id: newConvId,
        title: 'Nueva conversación',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
      setConversations([newConversation])
      setActiveConversationId(newConvId)
      activeConversationIdRef.current = newConvId
    } else if (isOpen && !activeConversationId && conversations.length > 0) {
      // Si hay conversaciones pero no hay activa, activar la más reciente
      const mostRecentId = conversations[0].id
      setActiveConversationId(mostRecentId)
      activeConversationIdRef.current = mostRecentId
    }
  }, [isOpen, conversations, activeConversationId])

  useEffect(() => {
    if (isOpen && !wsRef.current) {
      connectWebSocket()
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [isOpen])

  const sendMessage = async (text: string): Promise<void> => {
    if (!text.trim()) return

    // Capturar conversación activa al momento de enviar
    const conversationAtSendTime = activeConversationIdRef.current

    addMessage({ text: text.trim(), sender: 'user' })
    // Marcar que ESTA conversación está esperando respuesta
    setTypingConversationId(conversationAtSendTime)

    try {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        if (!wsRef.current) {
          connectWebSocket()
          await new Promise(resolve => setTimeout(resolve, 500))
        }

        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          throw new Error('No hay conexión con el servidor')
        }
      }

      // Enviar mensaje CON el conversation_id para que el backend lo devuelva
      const messageData = {
        message: text.trim(),
        conversation_id: conversationAtSendTime  // Incluir conversación original
      }

      wsRef.current.send(JSON.stringify(messageData))

    } catch (error) {
      console.error('Error enviando mensaje:', error)
      // Limpiar typing solo si es la conversación que falló
      setTypingConversationId(prev =>
        prev === conversationAtSendTime ? null : prev
      )
      addMessage({
        text: 'Lo siento, hubo un error. Intenta nuevamente.',
        sender: 'assistant'
      }, conversationAtSendTime)  // Agregar mensaje de error a la conversación correcta
    }
  }

  const clearMessages = (): void => {
    if (activeConversationId) {
      setConversations(prev => prev.map(conv =>
        conv.id === activeConversationId
          ? { ...conv, messages: [], updatedAt: new Date().toISOString() }
          : conv
      ))
    }
  }

  const createNewConversation = (): void => {
    const newConvId = `conv_${Date.now()}`
    const newConversation: Conversation = {
      id: newConvId,
      title: 'Nueva conversación',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    setConversations(prev => [newConversation, ...prev])
    setActiveConversationId(newConvId)
    // Actualizar ref inmediatamente para evitar race conditions
    activeConversationIdRef.current = newConvId
  }

  const deleteConversation = (id: string): void => {
    setConversations(prev => prev.filter(conv => conv.id !== id))
    if (activeConversationId === id) {
      const remaining = conversations.filter(conv => conv.id !== id)
      const newActiveId = remaining.length > 0 ? remaining[0].id : null
      setActiveConversationId(newActiveId)
      activeConversationIdRef.current = newActiveId
    }
  }

  const switchConversation = (id: string): void => {
    setActiveConversationId(id)
    activeConversationIdRef.current = id
  }

  const toggleChat = (): void => {
    setIsOpen(prev => !prev)
  }

  const closeChat = (): void => {
    setIsOpen(false)
  }

  const openChat = (): void => {
    setIsOpen(true)
  }

  return (
    <ChatContext.Provider value={{
      isOpen,
      messages,
      isTyping,
      isConnected,
      sessionId,
      conversations,
      activeConversationId,
      addMessage,
      sendMessage,
      clearMessages,
      toggleChat,
      closeChat,
      openChat,
      createNewConversation,
      deleteConversation,
      switchConversation
    }}>
      {children}
    </ChatContext.Provider>
  )
}

export const useChat = (): ChatContextType => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat debe usarse dentro de ChatProvider')
  }
  return context
}

export default ChatContext
