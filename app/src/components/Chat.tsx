import React, { useState, useRef, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { MessageCircle, X, Maximize2, Minimize2, Trash2, Send, Bot, Menu } from 'lucide-react'
import { useChat } from '../context/ChatContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import { Button } from './ui/button'
import { Card } from './ui/card'
import ConversationList from './ConversationList'

export default function Chat() {
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
  const [showConversations, setShowConversations] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim()) return

    const messageText = inputValue
    setInputValue('')
    await sendMessage(messageText)
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (location.pathname === '/chat') {
    return null
  }

  return (
    <>
      {/* Floating Button */}
      <Button
        onClick={toggleChat}
        size="icon"
        className={`fixed bottom-6 right-6 z-40 h-16 w-16 rounded-full text-white shadow-xl transition-all hover:scale-110 ${
          isOpen ? 'scale-0' : 'scale-100'
        }`}
        style={{ backgroundColor: '#6e348d' }}
        aria-label="Abrir chat de ayuda"
      >
        <MessageCircle className="h-8 w-8" strokeWidth={2.5} fill="white" />
        {messages.length > 0 && !isOpen && (
          <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-red-600 text-xs font-bold shadow-md">
            {messages.filter(m => m.sender === 'assistant').length}
          </span>
        )}
      </Button>

      {/* Chat Window */}
      {isOpen && (
        <Card
          className={`fixed z-50 flex overflow-hidden shadow-2xl transition-all ${
            isExpanded
              ? 'inset-6 w-auto h-auto'
              : 'bottom-6 right-6 h-[600px] max-w-[calc(100vw-3rem)] max-h-[calc(100vh-3rem)]'
          } ${!isExpanded && (showConversations ? 'w-[700px]' : 'w-[400px]')}`}
        >
          {/* Conversation List Sidebar */}
          {showConversations && (
            <div className="w-[280px] flex-shrink-0">
              <ConversationList />
            </div>
          )}

          {/* Main Chat Area */}
          <div className="flex flex-1 flex-col">
            {/* Header */}
            <div className="flex items-center justify-between border-b px-4 py-4 text-white shadow-md" style={{ backgroundColor: '#6e348d', height: '81px' }}>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowConversations(!showConversations)}
                  className="h-9 w-9 text-white hover:bg-white/20 hover:text-white transition-colors flex-shrink-0"
                  title="Historial de conversaciones"
                >
                  <Menu className="h-5 w-5" strokeWidth={2} />
                </Button>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 shadow-sm flex-shrink-0">
                  <Bot className="h-6 w-6" strokeWidth={2} />
                </div>
                <div className="flex-shrink-0">
                  <h3 className="font-semibold text-base whitespace-nowrap">Asistente La Tiendita</h3>
                  <p className="text-xs text-white/90 whitespace-nowrap">En línea</p>
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="h-9 w-9 text-white hover:bg-white/20 hover:text-white transition-colors"
                  title={isExpanded ? 'Modo ventana' : 'Expandir'}
                >
                  {isExpanded ? <Minimize2 className="h-5 w-5" strokeWidth={2} /> : <Maximize2 className="h-5 w-5" strokeWidth={2} />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearMessages}
                  className="h-9 w-9 text-white hover:bg-white/20 hover:text-white transition-colors"
                  title="Limpiar conversación"
                >
                  <Trash2 className="h-5 w-5" strokeWidth={2} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={closeChat}
                  className="h-9 w-9 text-white hover:bg-white/20 hover:text-white transition-colors"
                  title="Cerrar chat"
                >
                  <X className="h-5 w-5" strokeWidth={2} />
                </Button>
              </div>
            </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto bg-gray-50 p-4">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full shadow-lg" style={{ backgroundColor: '#f3e8ff' }}>
                  <Bot className="h-10 w-10" style={{ color: '#6e348d' }} strokeWidth={2} />
                </div>
                <h4 className="mb-2 text-lg font-semibold text-gray-900">
                  ¡Hola! Soy tu asistente
                </h4>
                <p className="mb-6 max-w-sm text-sm text-gray-600">
                  Estoy aquí para ayudarte con cualquier duda sobre productos, pedidos o navegación en la tienda.
                </p>
                <div className="space-y-2 w-full max-w-xs">
                  <Button
                    variant="outline"
                    onClick={() => sendMessage('¿Qué productos me recomiendan?')}
                    className="w-full justify-start text-sm hover:border-[#6e348d] hover:text-[#6e348d] transition-colors"
                  >
                    ¿Qué productos me recomiendan?
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => sendMessage('Ayuda con mi pedido')}
                    className="w-full justify-start text-sm hover:border-[#6e348d] hover:text-[#6e348d] transition-colors"
                  >
                    Ayuda con mi pedido
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => sendMessage('¿Cómo puedo contactarlos?')}
                    className="w-full justify-start text-sm hover:border-[#6e348d] hover:text-[#6e348d] transition-colors"
                  >
                    ¿Cómo puedo contactarlos?
                  </Button>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`mb-4 flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[80%] ${message.sender === 'user' ? 'order-2' : 'order-1'}`}>
                      <div
                        className={`rounded-lg px-4 py-2 shadow-sm ${
                          message.sender === 'user'
                            ? 'text-white'
                            : 'border bg-white text-gray-900'
                        }`}
                        style={message.sender === 'user' ? { backgroundColor: '#6e348d' } : {}}
                      >
                        <p className="whitespace-pre-wrap text-sm">{message.text}</p>

                        {/* Products */}
                        {message.products && message.products.length > 0 && (
                          <div className="mt-3 space-y-2">
                            <div className="text-xs font-semibold">Productos encontrados:</div>
                            {message.products.slice(0, 3).map((product: any, idx: number) => {
                              const imageUrl = getProductImageUrl(product.id)
                              const fallbackUrl = getFallbackImageUrl()
                              return (
                                <Card
                                  key={product.id || idx}
                                  className="p-3"
                                >
                                  <div className="flex gap-3">
                                    {imageUrl && (
                                      <img
                                        src={imageUrl}
                                        alt={product.name}
                                        className="h-16 w-16 rounded-md object-cover"
                                        onError={(e) => {
                                          const target = e.target as HTMLImageElement
                                          if (target.src !== fallbackUrl) {
                                            target.src = fallbackUrl
                                          } else {
                                            target.style.display = 'none'
                                          }
                                        }}
                                      />
                                    )}
                                    <div className="flex-1">
                                      <h5 className="font-medium text-gray-900">
                                        {product.name}
                                      </h5>
                                      <div className="mt-1 flex items-center gap-2 text-xs">
                                        <span className="text-gray-600">
                                          {product.category}
                                        </span>
                                        <span className="font-semibold" style={{ color: '#6e348d' }}>
                                          ${product.price?.toFixed(2) || '0.00'}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                </Card>
                              )
                            })}
                          </div>
                        )}
                      </div>
                      <div
                        className={`mt-1 text-xs text-gray-500 ${
                          message.sender === 'user' ? 'text-right' : 'text-left'
                        }`}
                      >
                        {formatTime(message.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="mb-4 flex justify-start">
                    <div className="max-w-[80%] rounded-lg border bg-white px-4 py-3">
                      <div className="flex gap-1">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]"></span>
                        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]"></span>
                        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="border-t bg-white p-4">
            <div className="flex gap-2">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe tu mensaje..."
                className="flex-1 resize-none rounded-md border border-gray-300 px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                rows={1}
                style={{
                  minHeight: '2.5rem',
                  maxHeight: '6rem'
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement
                  target.style.height = 'auto'
                  target.style.height = target.scrollHeight + 'px'
                }}
              />
              <Button
                type="submit"
                size="icon"
                className="h-10 w-10 shadow-sm text-white"
                style={{ backgroundColor: '#6e348d' }}
                disabled={!inputValue.trim() || isTyping}
              >
                <Send className="h-5 w-5" strokeWidth={2} />
              </Button>
            </div>
          </form>
          </div>
        </Card>
      )}
    </>
  )
}
