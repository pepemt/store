import { useState, useRef, useEffect } from 'react'
import { Send, Bot, Trash2 } from 'lucide-react'
import { useChat } from '../context/ChatContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'

export default function ChatPage() {
  const { messages, isTyping, sendMessage, clearMessages } = useChat()
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim()) return

    const messageText = inputValue
    setInputValue('')
    await sendMessage(messageText)
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="flex h-[calc(100vh-180px)] bg-gray-50">
      <div className="container mx-auto flex flex-col p-4">
        <div className="mb-4 flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-600">
              <Bot className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Asistente La Tiendita</h1>
              <p className="text-sm text-gray-600">En línea</p>
            </div>
          </div>
          <button
            onClick={clearMessages}
            className="flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4" />
            Limpiar
          </button>
        </div>

        <div className="flex-1 overflow-y-auto rounded-lg border border-gray-200 bg-white p-6">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-primary-100">
                <Bot className="h-10 w-10 text-primary-600" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-gray-900">¡Hola! Soy tu asistente</h2>
              <p className="mb-6 max-w-md text-gray-600">
                Estoy aquí para ayudarte con cualquier duda sobre productos, pedidos o navegación en la tienda.
              </p>
              <div className="space-y-2">
                <button
                  onClick={() => sendMessage('¿Qué productos me recomiendan?')}
                  className="block w-full rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm text-gray-700 hover:bg-gray-50"
                >
                  ¿Qué productos me recomiendan?
                </button>
                <button
                  onClick={() => sendMessage('Ayuda con mi pedido')}
                  className="block w-full rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Ayuda con mi pedido
                </button>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`mb-4 flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[70%] ${message.sender === 'user' ? 'order-2' : 'order-1'}`}>
                    <div
                      className={`rounded-lg px-4 py-3 ${
                        message.sender === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'border border-gray-200 bg-gray-50 text-gray-900'
                      }`}
                    >
                      <p className="whitespace-pre-wrap text-sm">{message.text}</p>

                      {message.products && message.products.length > 0 && (
                        <div className="mt-3 space-y-2">
                          <div className="text-xs font-semibold">Productos encontrados:</div>
                          {message.products.slice(0, 3).map((product: any, idx: number) => {
                            const imageUrl = getProductImageUrl(product.id)
                            const fallbackUrl = getFallbackImageUrl()
                            return (
                              <div
                                key={product.id || idx}
                                className="rounded-md border border-gray-200 bg-white p-3"
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
                                    <h5 className="font-medium text-gray-900">{product.name}</h5>
                                    <div className="mt-1 flex items-center gap-2 text-xs">
                                      <span className="text-gray-600">{product.category}</span>
                                      <span className="font-semibold text-primary-600">
                                        ${product.price?.toFixed(2) || '0.00'}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
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
                  <div className="max-w-[70%] rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
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

        <form onSubmit={handleSubmit} className="mt-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Escribe tu mensaje..."
              className="flex-1 rounded-lg border border-gray-300 px-4 py-3 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isTyping}
              className="flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-5 w-5" />
              Enviar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
