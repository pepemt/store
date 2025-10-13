import React, { createContext, useContext, useState, useEffect } from 'react'

const ChatContext = createContext()

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

  useEffect(() => {
    localStorage.setItem('tiendita_chat_messages', JSON.stringify(messages))
  }, [messages])

  const addMessage = (message) => {
    const newMessage = {
      id: Date.now() + Math.random(),
      text: message.text,
      sender: message.sender, // 'user' o 'assistant'
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, newMessage])
    return newMessage
  }

  const sendMessage = async (text) => {
    if (!text.trim()) return

    // Agregar mensaje del usuario
    addMessage({ text: text.trim(), sender: 'user' })
    
    // Mostrar indicador de typing
    setIsTyping(true)

    try {
      // Simular respuesta del LLM (aquí conectarás con tu LLM)
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
      
      // Respuesta mock del asistente
      const responses = [
        "¡Hola! Soy tu asistente de La Tiendita. ¿En qué puedo ayudarte?",
        "Claro, puedo ayudarte con información sobre productos, pedidos o cualquier duda que tengas.",
        "¿Te gustaría que te recomiende algunos productos populares?",
        "Si necesitas ayuda con tu carrito o proceso de compra, estaré encantado de asistirte.",
        "¿Hay algún producto específico que estés buscando?",
        "Puedo ayudarte a encontrar las mejores ofertas de nuestra tienda."
      ]
      
      const randomResponse = responses[Math.floor(Math.random() * responses.length)]
      addMessage({ text: randomResponse, sender: 'assistant' })
      
    } catch (error) {
      console.error('Error enviando mensaje:', error)
      addMessage({ 
        text: 'Lo siento, hubo un error. Intenta nuevamente.', 
        sender: 'assistant' 
      })
    } finally {
      setIsTyping(false)
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