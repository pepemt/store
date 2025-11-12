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
  const hostname = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'localhost'
    : window.location.hostname
  const port = import.meta.env.VITE_API_PORT || '8000'
  return `${protocol}//${hostname}:${port}/api/v1/chat/ws/chat`
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
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)

  const messages = conversations.find(c => c.id === activeConversationId)?.messages || []

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const customerIdRef = useRef<string | null>(null)

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

  const addMessage = (message: Partial<ChatMessage>): ChatMessage => {
    const newMessage: ChatMessage = {
      id: Date.now() + Math.random(),
      text: message.text || '',
      sender: message.sender || 'user',
      timestamp: new Date().toISOString(),
      products: message.products || null,
      intent: message.intent || null
    }

    setConversations(prev => {
      // Si hay conversación activa, agregar el mensaje a esa conversación
      const activeConv = prev.find(c => c.id === activeConversationId)

      if (activeConv) {
        return prev.map(conv =>
          conv.id === activeConversationId
            ? {
                ...conv,
                messages: [...conv.messages, newMessage],
                updatedAt: new Date().toISOString()
              }
            : conv
        )
      }

      // Si no hay conversación activa o no se encuentra, buscar la más reciente
      // o crear una nueva solo si no hay ninguna
      if (prev.length > 0) {
        // Agregar a la conversación más reciente (la primera en el array)
        const mostRecent = prev[0]
        setActiveConversationId(mostRecent.id)

        return prev.map((conv, index) =>
          index === 0
            ? {
                ...conv,
                messages: [...conv.messages, newMessage],
                updatedAt: new Date().toISOString()
              }
            : conv
        )
      }

      // Crear nueva conversación solo si no hay ninguna
      const newConvId = `conv_${Date.now()}`
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
        setIsTyping(false)
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
              setIsTyping(true)
              break

            case 'message':
              setIsTyping(false)
              addMessage({
                text: data.message,
                sender: 'assistant',
                products: data.products || null,
                intent: data.intent || null
              })
              if (data.session_id) {
                setSessionId(data.session_id)
              }
              break

            case 'error':
              setIsTyping(false)
              addMessage({
                text: data.message || 'Lo siento, hubo un error. Intenta nuevamente.',
                sender: 'assistant'
              })
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
        setIsTyping(false)

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

    addMessage({ text: text.trim(), sender: 'user' })
    setIsTyping(true)

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

      const messageData = {
        message: text.trim()
      }

      wsRef.current.send(JSON.stringify(messageData))

    } catch (error) {
      console.error('Error enviando mensaje:', error)
      setIsTyping(false)
      addMessage({
        text: 'Lo siento, hubo un error. Intenta nuevamente.',
        sender: 'assistant'
      })
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
  }

  const deleteConversation = (id: string): void => {
    setConversations(prev => prev.filter(conv => conv.id !== id))
    if (activeConversationId === id) {
      const remaining = conversations.filter(conv => conv.id !== id)
      setActiveConversationId(remaining.length > 0 ? remaining[0].id : null)
    }
  }

  const switchConversation = (id: string): void => {
    setActiveConversationId(id)
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
