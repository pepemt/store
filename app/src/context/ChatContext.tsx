import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react'

interface ChatMessage {
  id: number
  text: string
  sender: 'user' | 'assistant'
  timestamp: string
  products?: any[] | null
  intent?: string | null
}

interface ChatContextType {
  isOpen: boolean
  messages: ChatMessage[]
  isTyping: boolean
  isConnected: boolean
  sessionId: string | null
  addMessage: (message: Partial<ChatMessage>) => ChatMessage
  sendMessage: (text: string) => Promise<void>
  clearMessages: () => void
  toggleChat: () => void
  closeChat: () => void
  openChat: () => void
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
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('tiendita_chat_messages') || '[]')
    } catch {
      return []
    }
  })
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)

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
    localStorage.setItem('tiendita_chat_messages', JSON.stringify(messages))
  }, [messages])

  const addMessage = (message: Partial<ChatMessage>): ChatMessage => {
    const newMessage: ChatMessage = {
      id: Date.now() + Math.random(),
      text: message.text || '',
      sender: message.sender || 'user',
      timestamp: new Date().toISOString(),
      products: message.products || null,
      intent: message.intent || null
    }
    setMessages(prev => [...prev, newMessage])
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
              if (data.history && Array.isArray(data.history)) {
                const historyMessages = data.history.map((msg: any) => ({
                  id: Date.now() + Math.random() + Math.random(),
                  text: msg.content,
                  sender: msg.role === 'user' ? 'user' : 'assistant',
                  timestamp: new Date().toISOString()
                }))
                setMessages(historyMessages)
              }
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
    setMessages([])
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
      addMessage,
      sendMessage,
      clearMessages,
      toggleChat,
      closeChat,
      openChat
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
