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
  Scan,
  Brain,
  Search,
  Sparkles,
  MessageSquare,
  Loader2,
  CheckCircle2,
  XCircle,
  Zap,
  Star,
} from "lucide-react";
import { toast } from "sonner";
import { useChat, ThinkingStep, StepType } from "../context/ChatContext";
import { useCart } from "../context/CartContext";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Markdown } from "./ui/markdown";
import ConversationList from "./ConversationList";
import Avatar from "./Avatar";
import MicButton from "./ui/mic-button";

// Configuración de iconos y colores para cada tipo de paso
const STEP_CONFIG: Record<StepType, { icon: React.ElementType; color: string; label: string }> = {
  routing: { icon: Zap, color: "text-yellow-500", label: "Enrutando" },
  vision: { icon: Scan, color: "text-purple-500", label: "Analizando imagen" },
  classifier: { icon: Brain, color: "text-blue-500", label: "Clasificando" },
  chat: { icon: MessageSquare, color: "text-green-500", label: "Generando respuesta" },
  search_refine: { icon: Sparkles, color: "text-amber-500", label: "Refinando búsqueda" },
  search_v1: { icon: Search, color: "text-cyan-500", label: "Búsqueda V1" },
  search_v2: { icon: Search, color: "text-teal-500", label: "Búsqueda V2" },
  search_v3: { icon: Search, color: "text-emerald-500", label: "Búsqueda V3" },
  search_parallel: { icon: Zap, color: "text-indigo-500", label: "Búsqueda paralela" },
  discriminator: { icon: Star, color: "text-orange-500", label: "Seleccionando mejores" },
  response_gen: { icon: MessageSquare, color: "text-pink-500", label: "Preparando respuesta" },
  review_search: { icon: Star, color: "text-rose-500", label: "Buscando por opiniones" },
};

// Componente para mostrar un paso individual
const ThinkingStepItem: React.FC<{ step: ThinkingStep; isLast: boolean }> = ({ step, isLast }) => {
  const config = STEP_CONFIG[step.step_type] || { icon: Loader2, color: "text-gray-500", label: step.step_type };
  const Icon = config.icon;

  const getStatusIcon = () => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle2 className="h-3 w-3 text-green-500 flex-shrink-0" />;
      case 'error':
        return <XCircle className="h-3 w-3 text-red-500 flex-shrink-0" />;
      default:
        return <Loader2 className="h-3 w-3 animate-spin text-gray-400 flex-shrink-0" />;
    }
  };

  return (
    <div className={`flex items-start gap-2 py-1.5 ${step.status === 'started' && isLast ? 'animate-pulse' : ''}`}>
      <div className={`flex-shrink-0 p-1 rounded ${step.status === 'started' ? 'bg-gray-100' : 'bg-transparent'}`}>
        <Icon className={`h-3.5 w-3.5 ${config.color}`} />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`text-xs font-medium ${step.status === 'completed' ? 'text-gray-500' : 'text-gray-700'}`}>
            {step.title}
          </span>
          {getStatusIcon()}
          {step.duration_ms && (
            <span className="text-[10px] text-gray-400">
              {(step.duration_ms / 1000).toFixed(1)}s
            </span>
          )}
        </div>
        <p className={`text-[11px] break-words ${step.status === 'completed' ? 'text-gray-400' : 'text-gray-500'}`}>
          {step.description}
        </p>
      </div>
    </div>
  );
};

// Helper para agrupar pasos paralelos
const groupParallelSteps = (steps: ThinkingStep[]): (ThinkingStep | ThinkingStep[])[] => {
  const groupedSteps: (ThinkingStep | ThinkingStep[])[] = [];
  let currentParallelGroup: ThinkingStep[] = [];
  let currentGroupId: string | null = null;

  steps.forEach((step) => {
    if (step.is_parallel && step.parallel_group) {
      if (currentGroupId === step.parallel_group) {
        currentParallelGroup.push(step);
      } else {
        if (currentParallelGroup.length > 0) {
          groupedSteps.push([...currentParallelGroup]);
        }
        currentParallelGroup = [step];
        currentGroupId = step.parallel_group;
      }
    } else {
      if (currentParallelGroup.length > 0) {
        groupedSteps.push([...currentParallelGroup]);
        currentParallelGroup = [];
        currentGroupId = null;
      }
      groupedSteps.push(step);
    }
  });

  if (currentParallelGroup.length > 0) {
    groupedSteps.push(currentParallelGroup);
  }

  return groupedSteps;
};

// Componente para renderizar los pasos agrupados
const ThinkingStepsContent: React.FC<{ steps: ThinkingStep[]; isLive?: boolean }> = ({ steps, isLive = false }) => {
  const groupedSteps = groupParallelSteps(steps);

  return (
    <div className="space-y-0.5">
      {groupedSteps.map((item, idx) => {
        if (Array.isArray(item)) {
          // Grupo paralelo
          return (
            <div key={`parallel-${idx}`} className="pl-2 border-l-2 border-indigo-200 ml-1">
              <div className="flex items-center gap-1 mb-1">
                <Zap className="h-3 w-3 text-indigo-400" />
                <span className="text-[10px] text-indigo-500 font-medium">En paralelo</span>
              </div>
              {item.map((step, stepIdx) => (
                <ThinkingStepItem
                  key={`${step.step_type}-${stepIdx}`}
                  step={step}
                  isLast={isLive && idx === groupedSteps.length - 1 && stepIdx === item.length - 1}
                />
              ))}
            </div>
          );
        }
        return (
          <ThinkingStepItem
            key={`${item.step_type}-${idx}`}
            step={item}
            isLast={isLive && idx === groupedSteps.length - 1}
          />
        );
      })}
    </div>
  );
};

// Componente principal de pasos de pensamiento (en vivo, mientras procesa)
const ThinkingStepsDisplay: React.FC<{ steps: ThinkingStep[] }> = ({ steps }) => {
  if (steps.length === 0) return null;

  return (
    <div className="mb-4 flex justify-start">
      <div className="max-w-[85%] rounded-lg border bg-white px-3 py-2 shadow-sm">
        <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-gray-100">
          <Brain className="h-4 w-4 text-purple-600 animate-pulse" />
          <span className="text-xs font-semibold text-purple-700">Eyra está pensando...</span>
        </div>
        <ThinkingStepsContent steps={steps} isLive={true} />
      </div>
    </div>
  );
};

// Interfaz para StepResult
interface StepResultData {
  id: string;
  title: string;
  description: string;
  status: "completed" | "error" | "skipped";
  products?: any[];
  analysis?: any;
  error?: string;
}

// Componente para mostrar resultados de pasos multi-agente
const StepResultsDisplay: React.FC<{ stepResults: StepResultData[]; isExpanded?: boolean }> = ({ stepResults, isExpanded = false }) => {
  // By default, expand all steps that have products (skip step_1 analysis)
  const initialExpanded = new Set(
    stepResults
      .filter(s => s.products && s.products.length > 0)
      .map(s => s.id)
  );
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(initialExpanded);
  // Track which steps show all products
  const [showAllProducts, setShowAllProducts] = useState<Set<string>>(new Set());

  const toggleStep = (stepId: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  const toggleShowAll = (stepId: string) => {
    setShowAllProducts(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />;
      case "error":
        return <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />;
      case "skipped":
        return <XCircle className="h-3.5 w-3.5 text-orange-400 shrink-0" />;
      default:
        return <Loader2 className="h-3.5 w-3.5 animate-spin text-gray-400 shrink-0" />;
    }
  };

  // Filter to only show steps with products or analysis (skip empty steps)
  const visibleSteps = stepResults.filter(
    s => (s.products && s.products.length > 0) || s.analysis || s.status === "error"
  );

  if (visibleSteps.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-4 w-4 shrink-0" style={{ color: "#6e348d" }} />
        <span className="text-xs font-semibold text-gray-700">
          Resultados por categoría ({visibleSteps.length})
        </span>
      </div>

      {visibleSteps.map(step => {
        const isShowingAll = showAllProducts.has(step.id);
        const initialCount = isExpanded ? 6 : 4;  // Show more in expanded view
        const productsToShow = isShowingAll ? step.products : step.products?.slice(0, initialCount);
        const hasMoreProducts = step.products && step.products.length > initialCount;

        return (
          <div key={step.id} className="border rounded-lg overflow-hidden bg-white shadow-sm">
            {/* Header colapsable */}
            <button
              onClick={() => toggleStep(step.id)}
              className="w-full flex items-center justify-between p-2.5 bg-gradient-to-r from-gray-50 to-white hover:from-gray-100 hover:to-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                {getStatusIcon(step.status)}
                <span className="font-semibold text-xs text-gray-800 truncate">{step.title}</span>
              </div>
              <svg
                className={`h-4 w-4 text-gray-500 transition-transform duration-200 shrink-0 ml-2 ${
                  expandedSteps.has(step.id) ? "rotate-180" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Contenido expandible */}
            {expandedSteps.has(step.id) && (
              <div className="p-2.5 border-t bg-white">
                {/* Descripción del paso (siempre visible si existe) */}
                {step.description && (
                  <p className="text-xs text-gray-600 mb-2">{step.description}</p>
                )}

                {/* Productos - grid: 2 cols normal, 3 cols en vista expandida */}
                {productsToShow && productsToShow.length > 0 && (
                  <div className={`grid gap-1.5 ${isExpanded ? 'grid-cols-3' : 'grid-cols-2'}`}>
                    {productsToShow.map((product: any, idx: number) => (
                      <div key={product.id || idx} className="border rounded p-1.5 bg-gray-50 hover:shadow-sm transition-shadow">
                        <div className="aspect-square w-full bg-gray-100 rounded overflow-hidden mb-1">
                          <img
                            src={product.images?.[0]}
                            alt={product.name}
                            className="h-full w-full object-cover"
                          />
                        </div>
                        <p className="text-[10px] font-medium text-gray-800 leading-tight line-clamp-1" title={product.name}>
                          {product.name}
                        </p>
                        <p className="text-xs font-bold" style={{ color: "#6e348d" }}>
                          ${product.price?.toFixed(2)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Botón para ver más/menos productos */}
                {hasMoreProducts && (
                  <button
                    onClick={() => toggleShowAll(step.id)}
                    className="w-full mt-2 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                  >
                    {isShowingAll
                      ? "Ver menos"
                      : `Ver ${step.products!.length - initialCount} más`
                    }
                  </button>
                )}

                {/* Error si hay */}
                {step.error && (
                  <div className="text-xs text-red-600 bg-red-50 p-2 rounded mt-2 border border-red-200">
                    {step.error}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

// Componente colapsable para mostrar historial de pensamiento en mensajes pasados
const ThinkingStepsHistory: React.FC<{ steps: ThinkingStep[] }> = ({ steps }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!steps || steps.length === 0) return null;

  // Calcular tiempo total
  const totalTime = steps.reduce((acc, step) => acc + (step.duration_ms || 0), 0);

  return (
    <div className="mt-2 mb-1">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-gray-600 transition-colors"
      >
        <Brain className="h-3 w-3" />
        <span>
          {isExpanded ? 'Ocultar' : 'Ver'} proceso de pensamiento
          {totalTime > 0 && ` (${(totalTime / 1000).toFixed(1)}s)`}
        </span>
        <svg
          className={`h-3 w-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isExpanded && (
        <div className="mt-2 pl-2 border-l-2 border-purple-100">
          <ThinkingStepsContent steps={steps} isLive={false} />
        </div>
      )}
    </div>
  );
};

export default function Chat() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    isOpen,
    messages,
    isTyping,
    thinkingSteps,
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
  const [expandedProducts, setExpandedProducts] = useState<Set<number>>(new Set()); // Track which messages show all products
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toggleExpandProducts = (messageId: number) => {
    setExpandedProducts(prev => {
      const next = new Set(prev);
      if (next.has(messageId)) next.delete(messageId);
      else next.add(messageId);
      return next;
    });
  };


  // estado del avatar
  const [avatarState, setAvatarState] = useState<
    "standby" | "talking" | "thinking"
  >("standby");

  // URL de transcripción desde .env
  const API_BASE =
    (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";
  const TRANSCRIBE_URL = `${API_BASE}/transcribe`;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, thinkingSteps]);

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

  // Bloquear scroll del body cuando el chat está abierto en móvil
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = originalOverflow;
      };
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
      const t = setTimeout(() => setAvatarState("standby"), 6000);
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
    window.open(`/product/${productId}`, '_blank');
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

    console.log(
      `[Image] Selected file: ${file.name}, size: ${file.size} bytes (${(
        file.size / 1024
      ).toFixed(1)}KB), type: ${file.type}`
    );

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
      const result = e.target?.result as string;
      console.log(
        `[Image] Base64 preview length: ${result?.length || 0} chars`
      );
      setImagePreview(result);
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
        className={`fixed bottom-4 right-4 z-40 h-14 w-14 rounded-full text-white shadow-xl transition-all hover:scale-110 sm:bottom-6 sm:right-6 sm:h-16 sm:w-16 ${
          isOpen ? "scale-0" : "scale-100"
        }`}
        style={{ backgroundColor: "#6e348d" }}
        aria-label="Abrir chat de ayuda"
      >
        <MessageCircle className="h-7 w-7 sm:h-8 sm:w-8" strokeWidth={2.5} fill="white" />
        {messages.length > 0 && !isOpen && (
          <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-red-600 text-xs font-bold shadow-md">
            {messages.filter((m) => m.sender === "assistant").length}
          </span>
        )}
      </Button>

      {/* Chat Window */}
      {isOpen && (
        <Card
          className={`fixed z-50 flex overflow-hidden shadow-2xl transition-all duration-200 rounded-none sm:rounded-lg ${
            isExpanded
              ? "inset-2 sm:inset-6 rounded-lg"
              : "inset-0 sm:inset-auto sm:bottom-6 sm:right-6 sm:h-[600px] sm:w-[420px] sm:max-h-[calc(100vh-3rem)]"
          } ${!isExpanded && showConversations && "sm:w-[680px]"}`}
        >
          {/* Conversation List Sidebar */}
          {showConversations && (
            <>
              {/* Overlay para móvil */}
              <div
                className="absolute inset-0 bg-black/50 z-10 sm:hidden"
                onClick={() => setShowConversations(false)}
              />
              <div className="absolute inset-y-0 left-0 w-[260px] z-20 sm:relative sm:z-auto sm:w-[260px] flex-shrink-0 bg-white">
                <ConversationList />
              </div>
            </>
          )}

          {/* Main Chat Area */}
          <div className="flex flex-1 flex-col min-h-0">
            {/* Header */}
            <div
              className="flex items-center justify-between border-b px-4 py-4 text-white shadow-md flex-shrink-0"
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
                  <div className="fixed">
                    <div className="absolute scale-[0.3] origin-top-left left-[-4.4rem] top-[-4.3rem]">
                      <Avatar state={avatarState} />
                    </div>
                  </div>
                </div>

                <div className="flex-shrink-0">
                  <h3 className="font-semibold text-base whitespace-nowrap">
                    Eyra - AI
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
                  className="hidden sm:flex h-9 w-9 text-white hover:bg-white/20 hover:text-white transition-colors"
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
            <div className="flex-1 min-h-0 overflow-y-auto bg-gray-50 p-4">
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
                    ¡Hola! Soy Eyra, tu asistente de compras
                  </h4>
                  <p className="mb-6 max-w-sm text-sm text-gray-600">
                    Estoy aquí para ayudarte con cualquier duda sobre productos,
                    pedidos o navegación en la tienda. ¡Pídeme con confianza lo que quieras!
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
                  {messages.map((message) => {
                    const isReviewMode =
                      message.intent === "semantic_review_search" ||
                      message.search_method === "semantic_reviews";

                    return (
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
                                onClick={() =>
                                  window.open(message.image!, "_blank")
                                }
                              />
                            </div>
                          )}
                          {message.text &&
                            (message.sender === "assistant" ? (
                              <>
                                <Markdown className="text-gray-900">
                                  {message.text}
                                </Markdown>
                                {/* Mostrar historial de pensamiento colapsable */}
                                {message.thinkingSteps && message.thinkingSteps.length > 0 && (
                                  <ThinkingStepsHistory steps={message.thinkingSteps} />
                                )}

                                {/* Step Results (multi-step task display) */}
                                {(() => {
                                  const stepResults = (message as any).step_results;
                                  if (stepResults && stepResults.length > 0) {
                                    return <StepResultsDisplay stepResults={stepResults} isExpanded={isExpanded} />;
                                  }
                                  return null;
                                })()}
                              </>
                            ) : (
                              <p className="whitespace-pre-wrap text-sm">
                                {message.text}
                              </p>
                            ))}

                          {/* Products - Only show if NO step_results (avoid duplicate display) */}
                          {message.products && message.products.length > 0 && !(message as any).step_results?.length && (
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
                                  .slice(0, expandedProducts.has(message.id) ? undefined : (isExpanded ? 9 : 3))
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
                                          {isReviewMode && product.evidence_review && (
                                          <p className="text-[10px] text-gray-600 italic">
                                            Basado en esta opinión: “{product.evidence_review.length > 180
                                              ? product.evidence_review.slice(0, 180) + "…"
                                              : product.evidence_review}”
                                          </p>
                                        )}


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
                              {/* Botón para ver más/menos productos */}
                              {message.products.length > (isExpanded ? 9 : 3) && (
                                <button
                                  onClick={() => toggleExpandProducts(message.id)}
                                  className="w-full mt-2 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                                >
                                  {expandedProducts.has(message.id)
                                    ? "Ver menos"
                                    : `Ver ${message.products.length - (isExpanded ? 9 : 3)} más`
                                  }
                                </button>
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
                    );
                  })}

                  {isTyping && (
                    thinkingSteps.length > 0 ? (
                      <ThinkingStepsDisplay steps={thinkingSteps} />
                    ) : (
                      <div className="mb-4 flex justify-start">
                        <div className="max-w-[80%] rounded-lg border bg-white px-4 py-3">
                          <div className="flex gap-1">
                            <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]"></span>
                            <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]"></span>
                            <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></span>
                          </div>
                        </div>
                      </div>
                    )
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
              className="border-t bg-white p-4 relative flex-shrink-0"
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
                {/* Micrófono */}
                <MicButton
                  apiUrl={TRANSCRIBE_URL}
                  modelName="small"
                  maxMs={30000}
                  onTranscribed={async (text) => {
                    setAvatarState("thinking");
                    await sendMessage(text);
                  }}
                  className="h-10 w-10 flex-shrink-0 border-gray-300 hover:border-purple-500 hover:text-purple-600 transition-colors"
                  size="icon"
                  variant="outline"
                />

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
                  placeholder={
                    selectedImage
                      ? "Agrega un mensaje (opcional)..."
                      : "Escribe tu mensaje..."
                  }
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
