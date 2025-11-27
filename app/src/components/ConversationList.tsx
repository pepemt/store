import React, { useState } from 'react'
import { MessageSquare, Trash2, Plus } from 'lucide-react'
import { useChat } from '../context/ChatContext'
import { Button } from './ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog'

export default function ConversationList() {
  const {
    conversations,
    activeConversationId,
    switchConversation,
    deleteConversation,
    createNewConversation
  } = useChat()

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null)

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

    if (diffInHours < 24) {
      return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    } else if (diffInHours < 168) { // 7 días
      return date.toLocaleDateString('es-ES', { weekday: 'short' })
    } else {
      return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })
    }
  }

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setConversationToDelete(id)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = () => {
    if (conversationToDelete) {
      deleteConversation(conversationToDelete)
      setConversationToDelete(null)
    }
    setDeleteDialogOpen(false)
  }

  return (
    <div className="flex h-full flex-col border-r bg-gray-50">
      {/* Header */}
      <div className="flex items-center border-b px-3 py-4" style={{ backgroundColor: '#6e348d' }}>
        <Button
          onClick={createNewConversation}
          className="w-full shadow-sm text-white hover:bg-white/20 transition-colors font-semibold"
          variant="ghost"
          size="lg"
        >
          <Plus className="mr-2 h-5 w-5" strokeWidth={2} />
          Nueva conversación
        </Button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <MessageSquare className="mb-3 h-12 w-12 text-gray-400" />
            <p className="text-sm text-gray-600">No hay conversaciones</p>
            <p className="mt-1 text-xs text-gray-500">Inicia una nueva conversación</p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => switchConversation(conv.id)}
                className={`group relative cursor-pointer rounded-lg p-3 transition-colors ${
                  activeConversationId === conv.id
                    ? 'bg-white shadow-sm border-l-4'
                    : 'hover:bg-white/50'
                }`}
                style={
                  activeConversationId === conv.id
                    ? { borderLeftColor: '#6e348d' }
                    : {}
                }
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 overflow-hidden pr-2">
                    <div className="flex items-center gap-2">
                      <MessageSquare
                        className="h-4 w-4 flex-shrink-0"
                        style={{ color: activeConversationId === conv.id ? '#6e348d' : '#9ca3af' }}
                      />
                      <h4
                        className={`truncate text-sm font-medium ${
                          activeConversationId === conv.id ? 'text-gray-900' : 'text-gray-700'
                        }`}
                      >
                        {conv.title}
                      </h4>
                    </div>
                    <div className="mt-1 flex items-center justify-between text-xs text-gray-500">
                      <span>{conv.messages.length} mensajes</span>
                      <span>{formatDate(conv.updatedAt)}</span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => handleDeleteClick(e, conv.id)}
                    className="h-7 w-7 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-100 hover:text-red-600"
                    title="Eliminar conversación"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-white shadow-2xl border-2 border-gray-200">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl font-bold text-gray-900">
              ¿Eliminar conversación?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-base text-gray-600">
              Esta acción no se puede deshacer. La conversación será eliminada permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-2 border-gray-300 hover:bg-gray-100 font-semibold">
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="text-white shadow-lg hover:shadow-xl font-semibold"
              style={{ backgroundColor: '#ef4444' }}
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
