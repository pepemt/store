import React, { createContext, useContext, useState, useEffect, useRef } from 'react'

const ChatContext = createContext()

// WebSocket URL - puedes cambiarlo según tu configuración
// Si no está configurada, usa localhost o detecta el hostname
const getWebSocketURL = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  // Detectar el hostname (útil para desarrollo y producción)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const hostname = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'localhost' 
    : window.location.hostname
  const port = import.meta.env.VITE_API_PORT || '8000'
  return `${protocol}//${hostname}:${port}/api/v1/chat/ws/chat`
}

const WS_URL = getWebSocketURL()

export const ChatProvider = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState(() => {
    try { 
      return JSON.parse(localStorage.getItem('tiendita_chat_messages') || '[]') 
    } catch { 
      return [] 
    }
  })
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const customerIdRef = useRef(null)

  // Obtener customer_id del localStorage si está disponible
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

  const addMessage = (message) => {
    const newMessage = {
      id: Date.now() + Math.random(),
      text: message.text,
      sender: message.sender, // 'user' o 'assistant'
      timestamp: new Date().toISOString(),
      products: message.products || null, // Agregar productos si vienen
      intent: message.intent || null // Agregar intent si viene
    }
    setMessages(prev => [...prev, newMessage])
    return newMessage
  }

  const connectWebSocket = () => {
    try {
      // Construir URL con parámetros
      let wsUrl = WS_URL
      const params = []
      
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
        
        // Limpiar timeout de reconexión si existe
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
              // Guardar session_id si viene
              if (data.session_id) {
                setSessionId(data.session_id)
              }
              // Si hay historial, cargarlo
              if (data.history && Array.isArray(data.history)) {
                const historyMessages = data.history.map(msg => ({
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
              // Actualizar session_id si viene
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
        
        // Intentar reconectar si estaba conectado
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

  // Conectar WebSocket cuando se abre el chat o cuando cambia el usuario
  useEffect(() => {
    if (isOpen && !wsRef.current) {
      connectWebSocket()
    }

    return () => {
      // Limpiar al desmontar
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [isOpen])

  const sendMessage = async (text) => {
    if (!text.trim()) return

    // Agregar mensaje del usuario
    addMessage({ text: text.trim(), sender: 'user' })
    
    // Mostrar indicador de typing
    setIsTyping(true)

    try {
      // Verificar que WebSocket esté conectado
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        // Si no está conectado, intentar conectar
        if (!wsRef.current) {
          connectWebSocket()
          // Esperar un poco para que se conecte
          await new Promise(resolve => setTimeout(resolve, 500))
        }

        // Si aún no está conectado, mostrar error
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          throw new Error('No hay conexión con el servidor')
        }
      }

      // Enviar mensaje al WebSocket
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

  const clearMessages = () => {
    setMessages([])
  }

  const toggleChat = () => {
    setIsOpen(prev => !prev)
  }

  const closeChat = () => {
    setIsOpen(false)
  }

  const openChat = () => {
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

export const useChat = () => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat debe usarse dentro de ChatProvider')
  }
  return context
}

export default ChatContext