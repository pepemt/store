import React, { useState, useRef, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  MessageCircle,
  X,
  Maximize2,
  Minimize2,
  Trash2,
  Send,
  Bot,
  Menu,
  ShoppingCart,
  Eye,
  Package,
  ImageIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useChat } from "../context/ChatContext";
import { useCart } from "../context/CartContext";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import ConversationList from "./ConversationList";
import Avatar from "./Avatar";

export default function Chat() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    isOpen,
    messages,
    isTyping,
    sendMessage,
    clearMessages,
    toggleChat,
    closeChat,
  } = useChat();
  const { add } = useCart();

  const [inputValue, setInputValue] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const [showConversations, setShowConversations] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // estado del avatar
  const [avatarState, setAvatarState] = useState<
    "standby" | "talking" | "thinking"
  >("standby");

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    if (location.pathname === "/chat" && isOpen) {
      closeChat();
    }
  }, [location.pathname, isOpen, closeChat]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // sincroniza estado del avatar con escritura/respuesta
  useEffect(() => {
    if (isTyping) {
      setAvatarState("thinking");
      return;
    }
    const last = messages[messages.length - 1];
    if (last?.sender === "assistant") {
      setAvatarState("talking");
      const t = setTimeout(() => setAvatarState("standby"), 2500);
      return () => clearTimeout(t);
    }
    setAvatarState("standby");
  }, [isTyping, messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() && !selectedImage) return;

    const messageText = inputValue;
    const imageToSend = selectedImage;

    setInputValue("");
    clearSelectedImage();

    // mientras esperamos respuesta, "pensando"
    setAvatarState("thinking");
    await sendMessage(messageText, imageToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString("es-ES", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleViewProduct = (productId: number) => {
    navigate(`/product/${productId}`);
    closeChat();
  };

  const handleAddToCart = async (product: any) => {
    try {
      await add(
        {
          id: product.id,
          name: product.name,
          price: product.price,
          images: product.images || [],
        },
        1
      );
      toast.success("¡Producto agregado al carrito!", {
        description: `${product.name}`,
        duration: 3000,
      });
    } catch (error: any) {
      console.error("Error adding to cart:", error);
      toast.error("Error al agregar al carrito", {
        description: error?.message || "Por favor intenta nuevamente",
        duration: 4000,
      });
    }
  };

  // Image handling
  const handleImageSelect = useCallback((file: File) => {
    const allowedTypes = ["image/png", "image/jpeg", "image/jpg"];
    const maxSize = 5 * 1024 * 1024; // 5MB

    if (!allowedTypes.includes(file.type)) {
      toast.error("Tipo de imagen no soportado", {
        description: "Usa PNG o JPG",
      });
      return;
    }

    if (file.size > maxSize) {
      toast.error("Imagen muy grande", {
        description: "Máximo 5MB",
      });
      return;
    }

    setSelectedImage(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  const clearSelectedImage = useCallback(() => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleImageSelect(files[0]);
      }
    },
    [handleImageSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleImageSelect(files[0]);
      }
    },
    [handleImageSelect]
  );

  if (location.pathname === "/chat") {
    return null;
  }

  return (
    <>
      {/* Floating Button */}
      <Button
        onClick={toggleChat}
        size="icon"
        className={`fixed bottom-6 right-6 z-40 h-16 w-16 rounded-full text-white shadow-xl transition-all hover:scale-110 ${
          isOpen ? "scale-0" : "scale-100"
        }`}
        style={{ backgroundColor: "#6e348d" }}
        aria-label="Abrir chat de ayuda"
      >
        <MessageCircle className="h-8 w-8" strokeWidth={2.5} fill="white" />
        {messages.length > 0 && !isOpen && (
          <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-red-600 text-xs font-bold shadow-md">
            {messages.filter((m) => m.sender === "assistant").length}
          </span>
        )}
      </Button>

      {/* Chat Window */}
      {isOpen && (
        <Card
          className={`fixed z-50 flex overflow-hidden shadow-2xl transition-all ${
            isExpanded
              ? "inset-6 w-auto h-auto"
              : "bottom-6 right-6 h-[600px] max-w-[calc(100vw-3rem)] max-h-[calc(100vh-3rem)]"
          } ${!isExpanded && (showConversations ? "w-[700px]" : "w-[500px]")}`}
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
            <div
              className="flex items-center justify-between border-b px-4 py-4 text-white shadow-md"
              style={{ backgroundColor: "#6e348d" }}
            >
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowConversations(!showConversations)}
                  className="h-9 w-9 text-white hover:bg-white/20 hover:text-white transition-colors flex-shrink-0 z-[3000000]"
                  title="Historial de conversaciones"
                >
                  <Menu className="h-5 w-5" strokeWidth={2} />
                </Button>

                {/* Avatar mini */}
                <div className="relative flex items-center justify-center rounded-full bg-white/10 shadow-sm w-[3rem]">
                  {/* lo escalamos para que quepa en el header */}
                  <div className="fixed">
                    <div className="absolute scale-[0.3] origin-top-left left-[-4.4rem] top-[-4.3rem]">
                      <Avatar state={avatarState} />
                    </div>
                  </div>
                </div>

                <div className="flex-shrink-0">
                  <h3 className="font-semibold text-base whitespace-nowrap">
                    Asistente La Tiendita
                  </h3>
                  <p className="text-xs text-white/90 whitespace-nowrap">
                    {avatarState === "thinking"
                      ? "Pensando…"
                      : avatarState === "talking"
                      ? "Hablando…"
                      : "En línea"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="h-9 w-9 text-white hover:bg-white/20 hover:text-white transition-colors"
                  title={isExpanded ? "Modo ventana" : "Expandir"}
                >
                  {isExpanded ? (
                    <Minimize2 className="h-5 w-5" strokeWidth={2} />
                  ) : (
                    <Maximize2 className="h-5 w-5" strokeWidth={2} />
                  )}
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
                  <div
                    className="mb-4 flex h-20 w-20 items-center justify-center rounded-full shadow-lg"
                    style={{ backgroundColor: "#f3e8ff" }}
                  >
                    <Bot
                      className="h-10 w-10"
                      style={{ color: "#6e348d" }}
                      strokeWidth={2}
                    />
                  </div>
                  <h4 className="mb-2 text-lg font-semibold text-gray-900">
                    ¡Hola! Soy tu asistente
                  </h4>
                  <p className="mb-6 max-w-sm text-sm text-gray-600">
                    Estoy aquí para ayudarte con cualquier duda sobre productos,
                    pedidos o navegación en la tienda.
                  </p>
                  <div className="space-y-2 w-full max-w-xs">
                    <Button
                      variant="outline"
                      onClick={() =>
                        sendMessage("¿Qué productos me recomiendan?")
                      }
                      className="w-full justify-start text-sm hover:border-[#6e348d] hover:text-[#6e348d] transition-colors"
                    >
                      ¿Qué productos me recomiendan?
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => sendMessage("Ayuda con mi pedido")}
                      className="w-full justify-start text-sm hover:border-[#6e348d] hover:text-[#6e348d] transition-colors"
                    >
                      Ayuda con mi pedido
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => sendMessage("¿Cómo puedo contactarlos?")}
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
                      className={`mb-4 flex ${
                        message.sender === "user"
                          ? "justify-end"
                          : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[80%] ${
                          message.sender === "user" ? "order-2" : "order-1"
                        }`}
                      >
                        <div
                          className={`rounded-lg px-4 py-2 shadow-sm ${
                            message.sender === "user"
                              ? "text-white"
                              : "border bg-white text-gray-900"
                          }`}
                          style={
                            message.sender === "user"
                              ? { backgroundColor: "#6e348d" }
                              : {}
                          }
                        >
                          {/* Image thumbnail if present */}
                          {message.image && (
                            <div className="mb-2">
                              <img
                                src={message.image}
                                alt="Imagen adjunta"
                                className="max-w-[150px] max-h-[150px] rounded-lg object-cover cursor-pointer hover:opacity-90 transition-opacity"
                                onClick={() => window.open(message.image!, "_blank")}
                              />
                            </div>
                          )}
                          {message.text && (
                            <p className="whitespace-pre-wrap text-sm">
                              {message.text}
                            </p>
                          )}

                          {/* Products */}
                          {message.products && message.products.length > 0 && (
                            <div className="mt-3 space-y-2">
                              <div className="flex items-center gap-2 mb-2">
                                <Package
                                  className="h-4 w-4"
                                  style={{ color: "#6e348d" }}
                                />
                                <span className="text-xs font-semibold text-gray-700">
                                  {message.products.length} producto
                                  {message.products.length > 1 ? "s" : ""}{" "}
                                  encontrado
                                  {message.products.length > 1 ? "s" : ""}
                                </span>
                              </div>
                              <div
                                className={`grid ${
                                  isExpanded
                                    ? "grid-cols-3 gap-2"
                                    : "grid-cols-1 gap-3"
                                }`}
                              >
                                {message.products
                                  .slice(0, isExpanded ? 9 : 3)
                                  .map((product: any, idx: number) => {
                                    return (
                                      <Card
                                        key={product.id || idx}
                                        className="overflow-hidden hover:shadow-lg transition-shadow duration-200 group"
                                      >
                                        {/* Imagen del producto */}
                                        <div className="relative aspect-square w-full bg-gray-100">
                                          <img
                                            src={product.images?.[0]}
                                            alt={product.name}
                                            className="h-full w-full object-cover"
                                          />
                                          {/* Badges */}
                                          <div
                                            className={`absolute flex flex-col gap-1 ${
                                              isExpanded
                                                ? "top-1 right-1"
                                                : "top-2 right-2"
                                            }`}
                                          >
                                            {product.stock &&
                                              product.stock < 10 &&
                                              product.stock > 0 && (
                                                <span
                                                  className={`bg-orange-500 text-white font-bold rounded-full shadow ${
                                                    isExpanded
                                                      ? "text-[8px] px-1.5 py-0.5"
                                                      : "text-[10px] px-2 py-0.5"
                                                  }`}
                                                >
                                                  ¡Últimos!
                                                </span>
                                              )}
                                            {product.color && !isExpanded && (
                                              <span className="bg-white/90 text-gray-700 text-[10px] font-medium px-2 py-0.5 rounded-full shadow backdrop-blur-sm">
                                                {product.color}
                                              </span>
                                            )}
                                          </div>
                                        </div>

                                        {/* Info del producto */}
                                        <div
                                          className={`space-y-1.5 ${
                                            isExpanded ? "p-2" : "p-3"
                                          }`}
                                        >
                                          {/* Nombre y categoría */}
                                          <div>
                                            <h5
                                              className={`font-semibold text-gray-900 line-clamp-2 group-hover:text-[#6e348d] transition-colors ${
                                                isExpanded
                                                  ? "text-xs"
                                                  : "text-sm"
                                              }`}
                                            >
                                              {product.name}
                                            </h5>
                                            <p
                                              className={`text-gray-500 mt-0.5 ${
                                                isExpanded
                                                  ? "text-[10px]"
                                                  : "text-xs"
                                              }`}
                                            >
                                              {product.category ||
                                                "Sin categoría"}
                                            </p>
                                          </div>

                                          {/* Precio */}
                                          <div className="flex items-baseline gap-1">
                                            <span
                                              className={`font-bold ${
                                                isExpanded
                                                  ? "text-base"
                                                  : "text-lg"
                                              }`}
                                              style={{ color: "#6e348d" }}
                                            >
                                              $
                                              {product.price?.toFixed(2) ||
                                                "0.00"}
                                            </span>
                                            {product.stock !== undefined &&
                                              !isExpanded && (
                                                <span className="text-xs text-gray-500">
                                                  {product.stock > 0
                                                    ? `• ${product.stock} disponibles`
                                                    : "• Agotado"}
                                                </span>
                                              )}
                                          </div>

                                          {/* Botones de acción */}
                                          <div
                                            className={`flex gap-1.5 ${
                                              isExpanded ? "pt-0.5" : "pt-1"
                                            }`}
                                          >
                                            <Button
                                              size="sm"
                                              variant="outline"
                                              onClick={() =>
                                                handleViewProduct(product.id)
                                              }
                                              className={`flex-1 border-[#6e348d] text-[#6e348d] hover:bg-[#6e348d] hover:text-white transition-colors ${
                                                isExpanded
                                                  ? "text-[10px] h-7 px-1"
                                                  : "text-xs h-8"
                                              }`}
                                            >
                                              <Eye
                                                className={
                                                  isExpanded
                                                    ? "h-2.5 w-2.5 mr-0.5"
                                                    : "h-3 w-3 mr-1"
                                                }
                                              />
                                              Ver
                                            </Button>
                                            <Button
                                              size="sm"
                                              onClick={() =>
                                                handleAddToCart(product)
                                              }
                                              className={`flex-1 text-white hover:opacity-90 transition-opacity ${
                                                isExpanded
                                                  ? "text-[10px] h-7 px-1"
                                                  : "text-xs h-8"
                                              }`}
                                              style={{
                                                backgroundColor: "#6e348d",
                                              }}
                                              disabled={product.stock === 0}
                                            >
                                              <ShoppingCart
                                                className={
                                                  isExpanded
                                                    ? "h-2.5 w-2.5 mr-0.5"
                                                    : "h-3 w-3 mr-1"
                                                }
                                              />
                                              Añadir
                                            </Button>
                                          </div>
                                        </div>
                                      </Card>
                                    );
                                  })}
                              </div>
                              {/* Mensaje si hay más productos */}
                              {message.products.length >
                                (isExpanded ? 9 : 3) && (
                                <p className="text-xs text-gray-500 text-center pt-1">
                                  +
                                  {message.products.length -
                                    (isExpanded ? 9 : 3)}{" "}
                                  producto
                                  {message.products.length -
                                    (isExpanded ? 9 : 3) >
                                  1
                                    ? "s"
                                    : ""}{" "}
                                  más...
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                        <div
                          className={`mt-1 text-xs text-gray-500 ${
                            message.sender === "user"
                              ? "text-right"
                              : "text-left"
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
            <form
              onSubmit={handleSubmit}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className="border-t bg-white p-4 relative"
            >
              {/* Drag overlay */}
              {isDragOver && (
                <div className="absolute inset-0 bg-purple-100/90 border-2 border-dashed border-purple-500 rounded-lg flex items-center justify-center z-10">
                  <div className="text-center">
                    <ImageIcon className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                    <p className="text-sm font-medium text-purple-700">
                      Suelta la imagen aquí
                    </p>
                  </div>
                </div>
              )}

              {/* Image preview */}
              {imagePreview && (
                <div className="mb-3 relative inline-block">
                  <img
                    src={imagePreview}
                    alt="Preview"
                    className="max-h-24 rounded-lg object-cover border border-gray-200"
                  />
                  <button
                    type="button"
                    onClick={clearSelectedImage}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition-colors shadow-md"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}

              <div className="flex gap-2">
                {/* Hidden file input */}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileInputChange}
                  accept="image/png,image/jpeg,image/jpg"
                  className="hidden"
                />

                {/* Image button */}
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => fileInputRef.current?.click()}
                  className="h-10 w-10 flex-shrink-0 border-gray-300 hover:border-purple-500 hover:text-purple-600 transition-colors"
                  title="Adjuntar imagen"
                >
                  <ImageIcon className="h-5 w-5" strokeWidth={2} />
                </Button>

                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => {
                    setInputValue(e.target.value);
                    setAvatarState("thinking");
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder={selectedImage ? "Agrega un mensaje (opcional)..." : "Escribe tu mensaje..."}
                  className="flex-1 resize-none rounded-md border border-gray-300 px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  rows={1}
                  style={{
                    minHeight: "2.5rem",
                    maxHeight: "6rem",
                  }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "auto";
                    target.style.height = target.scrollHeight + "px";
                  }}
                />
                <Button
                  type="submit"
                  size="icon"
                  className="h-10 w-10 shadow-sm text-white"
                  style={{ backgroundColor: "#6e348d" }}
                  disabled={(!inputValue.trim() && !selectedImage) || isTyping}
                >
                  <Send className="h-5 w-5" strokeWidth={2} />
                </Button>
              </div>
            </form>
          </div>
        </Card>
      )}
    </>
  );
}
