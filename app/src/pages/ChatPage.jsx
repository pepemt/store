import React, { useState, useRef, useEffect } from 'react'
import { useChat } from '../context/ChatContext'
import { useNavigate } from 'react-router-dom'
import '../styles/ChatPage.css'

export default function ChatPage() {
  const navigate = useNavigate()
  const { 
    messages, 
    isTyping, 
    sendMessage, 
    clearMessages 
  } = useChat()
  
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

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

  const handleBack = () => {
    navigate(-1)
  }

  return (
    <div className="chat-page">
      {/* Header de la página */}
      <div className="chat-page-header">
        <button 
          onClick={handleBack}
          className="back-button"
          title="Volver"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="m15 18-6-6 6-6"/>
          </svg>
        </button>
        
        <div className="chat-page-info">
          <div className="chat-page-avatar">🤖</div>
          <div className="chat-page-title">
            <h1>Asistente La Tiendita</h1>
            <p className="chat-page-status">En línea • Respuesta inmediata</p>
          </div>
        </div>
        
        <div className="chat-page-actions">
          <button 
            onClick={clearMessages}
            className="chat-page-action-button"
            title="Limpiar conversación"
          >
            🗑️
          </button>
        </div>
      </div>

      {/* Contenido principal del chat */}
      <div className="chat-page-content">
        <div className="chat-page-messages">
          {messages.length === 0 ? (
            <div className="chat-page-welcome">
              <div className="welcome-page-avatar">🤖</div>
              <h2 className="welcome-page-title">¡Bienvenido al chat de soporte!</h2>
              <p className="welcome-page-text">
                Estoy aquí para ayudarte con cualquier duda sobre productos, 
                pedidos, envíos o cualquier consulta sobre La Tiendita de la Esquina. 
                ¿En qué puedo asistirte hoy?
              </p>
              <div className="welcome-page-suggestions">
                <div className="suggestions-grid">
                  <button 
                    onClick={() => sendMessage('¿Qué productos me recomiendan?')}
                    className="suggestion-card"
                  >
                    <span className="suggestion-icon">🛍️</span>
                    <span className="suggestion-text">Recomendaciones de productos</span>
                  </button>
                  <button 
                    onClick={() => sendMessage('Ayuda con mi pedido')}
                    className="suggestion-card"
                  >
                    <span className="suggestion-icon">📦</span>
                    <span className="suggestion-text">Estado de mi pedido</span>
                  </button>
                  <button 
                    onClick={() => sendMessage('¿Cómo puedo contactarlos?')}
                    className="suggestion-card"
                  >
                    <span className="suggestion-icon">📞</span>
                    <span className="suggestion-text">Información de contacto</span>
                  </button>
                  <button 
                    onClick={() => sendMessage('¿Cuáles son los métodos de pago?')}
                    className="suggestion-card"
                  >
                    <span className="suggestion-icon">💳</span>
                    <span className="suggestion-text">Métodos de pago</span>
                  </button>
                  <button 
                    onClick={() => sendMessage('¿Hacen envíos a domicilio?')}
                    className="suggestion-card"
                  >
                    <span className="suggestion-icon">🚚</span>
                    <span className="suggestion-text">Información de envíos</span>
                  </button>
                  <button 
                    onClick={() => sendMessage('¿Cuál es el horario de atención?')}
                    className="suggestion-card"
                  >
                    <span className="suggestion-icon">🕐</span>
                    <span className="suggestion-text">Horarios de atención</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div 
                  key={message.id} 
                  className={`chat-page-message ${message.sender}`}
                >
                  <div className="message-page-content">
                    <div className="message-page-text">{message.text}</div>
                    <div className="message-page-time">
                      {formatTime(message.timestamp)}
                    </div>
                  </div>
                </div>
              ))}
              
              {isTyping && (
                <div className="chat-page-message assistant">
                  <div className="message-page-content">
                    <div className="typing-page-indicator">
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
      </div>

      {/* Input de mensaje */}
      <div className="chat-page-input-container">
        <form onSubmit={handleSubmit} className="chat-page-input-form">
          <div className="chat-page-input-wrapper">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Escribe tu mensaje aquí..."
              className="chat-page-input"
              rows="1"
              style={{
                height: 'auto',
                minHeight: '3rem',
                maxHeight: '8rem'
              }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = e.target.scrollHeight + 'px'
              }}
            />
            <button 
              type="submit"
              className="chat-page-send-button"
              disabled={!inputValue.trim() || isTyping}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}