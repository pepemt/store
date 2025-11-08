import React, { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useChat } from '../context/ChatContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import '../styles/Chat.css'

export default function Chat() {
  const navigate = useNavigate()
  const location = useLocation()
  const { 
    isOpen, 
    messages, 
    isTyping, 
    sendMessage, 
    clearMessages, 
    toggleChat, 
    closeChat 
  } = useChat()
  
  const [inputValue, setInputValue] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  // Cerrar chat flotante cuando estemos en la página del chat
  useEffect(() => {
    if (location.pathname === '/chat' && isOpen) {
      closeChat()
    }
  }, [location.pathname, isOpen, closeChat])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!inputValue.trim()) return

    const messageText = inputValue
    setInputValue('')
    await sendMessage(messageText)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleExpandToggle = () => {
    setIsExpanded(!isExpanded)
  }

  const handleOpenFullPage = () => {
    // Solo navegar, el chat se cerrará automáticamente al cambiar de página
    navigate('/chat')
  }

  // No mostrar el chat flotante si estamos en la página del chat
  if (location.pathname === '/chat') {
    return null
  }

  return (
    <>
      {/* Botón flotante */}
      <button 
        onClick={toggleChat}
        className={`chat-toggle-button ${isOpen ? 'open' : ''}`}
        aria-label="Abrir chat de ayuda"
      >
        {isOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        )}
        {messages.length > 0 && !isOpen && (
          <span className="chat-notification-badge">
            {messages.filter(m => m.sender === 'assistant').length}
          </span>
        )}
      </button>

      {/* Ventana de chat */}
      {isOpen && (
        <div className={`chat-window ${isExpanded ? 'expanded' : ''}`}>
          {/* Header del chat */}
          <div className="chat-header">
            <div className="chat-header-info">
              <div className="chat-avatar">🤖</div>
              <div className="chat-header-text">
                <h3 className="chat-title">Asistente La Tiendita</h3>
                <p className="chat-status">En línea</p>
              </div>
            </div>
            <div className="chat-header-actions">
              <button 
                onClick={handleExpandToggle}
                className="chat-action-button"
                title={isExpanded ? "Modo ventana" : "Expandir"}
              >
                {isExpanded ? '🗗' : '🗖'}
              </button>
              <button 
                onClick={handleOpenFullPage}
                className="chat-action-button"
                title="Abrir en página completa"
              >
                🔗
              </button>
              <button 
                onClick={clearMessages}
                className="chat-action-button"
                title="Limpiar conversación"
              >
                🗑️
              </button>
              <button 
                onClick={closeChat}
                className="chat-action-button"
                title="Cerrar chat"
              >
                ❌
              </button>
            </div>
          </div>

          {/* Área de mensajes */}
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="chat-welcome">
                <div className="welcome-avatar">🤖</div>
                <h4 className="welcome-title">¡Hola! Soy tu asistente</h4>
                <p className="welcome-text">
                  Estoy aquí para ayudarte con cualquier duda sobre productos, 
                  pedidos o navegación en la tienda. ¿En qué puedo asistirte?
                </p>
                <div className="welcome-suggestions">
                  <button 
                    onClick={() => sendMessage('¿Qué productos me recomiendan?')}
                    className="suggestion-button"
                  >
                    ¿Qué productos me recomiendan?
                  </button>
                  <button 
                    onClick={() => sendMessage('Ayuda con mi pedido')}
                    className="suggestion-button"
                  >
                    Ayuda con mi pedido
                  </button>
                  <button 
                    onClick={() => sendMessage('¿Cómo puedo contactarlos?')}
                    className="suggestion-button"
                  >
                    ¿Cómo puedo contactarlos?
                  </button>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <div 
                    key={message.id} 
                    className={`chat-message ${message.sender}`}
                  >
                    <div className="message-content">
                      <div className="message-text">{message.text}</div>
                      
                      {/* Mostrar productos si vienen en el mensaje */}
                      {message.products && message.products.length > 0 && (
                        <div className="message-products">
                          <div className="products-header">Productos encontrados:</div>
                          <div className="products-list">
                            {message.products.slice(0, 3).map((product, idx) => {
                              const imageUrl = getProductImageUrl(product.id);
                              const fallbackUrl = getFallbackImageUrl();
                              return (
                                <div key={product.id || idx} className="product-card">
                                  {imageUrl && (
                                    <div className="product-image-container">
                                      <img 
                                        src={imageUrl} 
                                        alt={product.name}
                                        className="product-image"
                                        onError={(e) => {
                                          // Si falla la imagen con el ID, intentar con "komo"
                                          if (e.target.src !== fallbackUrl) {
                                            e.target.src = fallbackUrl;
                                          } else {
                                            // Si también falla "komo", ocultar la imagen
                                            e.target.style.display = 'none';
                                          }
                                        }}
                                      />
                                    </div>
                                  )}
                                  <div className="product-content">
                                    <h4 className="product-name">{product.name}</h4>
                                    <div className="product-info">
                                      <span className="product-category">{product.category}</span>
                                      <span className="product-price">${product.price?.toFixed(2) || '0.00'}</span>
                                    </div>
                                    {product.description && (
                                      <p className="product-description">{product.description}</p>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      
                      <div className="message-time">
                        {formatTime(message.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}
                
                {isTyping && (
                  <div className="chat-message assistant">
                    <div className="message-content">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input de mensaje */}
          <form onSubmit={handleSubmit} className="chat-input-form">
            <div className="chat-input-container">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe tu mensaje..."
                className="chat-input"
                rows="1"
                style={{
                  height: 'auto',
                  minHeight: '2.5rem',
                  maxHeight: '6rem'
                }}
                onInput={(e) => {
                  e.target.style.height = 'auto'
                  e.target.style.height = e.target.scrollHeight + 'px'
                }}
              />
              <button 
                type="submit"
                className="chat-send-button"
                disabled={!inputValue.trim() || isTyping}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
                </svg>
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  )
}