import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2, Plus, Minus, ShoppingBag, ArrowRight, Loader } from 'lucide-react'
import { useCart } from '../context/CartContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog'

interface ItemToDelete {
  id: string | number
  name: string
}

export default function Cart() {
  const { items, updateQty, remove, clear, total, count, loading, mutating } = useCart()

  // Estado para el dialog de eliminar item
  const [itemToDelete, setItemToDelete] = useState<ItemToDelete | null>(null)
  // Estado para el dialog de vaciar carrito
  const [showClearDialog, setShowClearDialog] = useState(false)

  const handleUpdateQuantity = async (id: string | number, newQty: number) => {
    try {
      await updateQty(id, newQty)
    } catch (err) {
      console.error('Error updating quantity:', err)
    }
  }

  const handleRemove = async () => {
    if (!itemToDelete) return
    try {
      await remove(itemToDelete.id)
    } catch (err) {
      console.error('Error removing item:', err)
    } finally {
      setItemToDelete(null)
    }
  }

  const handleClear = async () => {
    try {
      await clear()
    } catch (err) {
      console.error('Error clearing cart:', err)
    } finally {
      setShowClearDialog(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center">
        <Loader className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="min-h-[calc(100vh-200px)] bg-gray-50">
        <div className="container mx-auto px-4 py-12">
          <div className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center">
            <ShoppingBag className="mx-auto mb-4 h-16 w-16 text-gray-400" />
            <h2 className="mb-2 text-2xl font-bold text-gray-900">Tu carrito está vacío</h2>
            <p className="mb-6 text-gray-600">Agrega productos para comenzar tu compra</p>
            <Link
              to="/products"
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white hover:bg-primary-700"
            >
              Ver Productos
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="min-h-[calc(100vh-200px)] bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">Carrito de Compras</h1>
            <button
              onClick={() => setShowClearDialog(true)}
              disabled={mutating}
              className="flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              Vaciar carrito
            </button>
          </div>

          <div className="grid gap-8 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              {items.map((item) => {
                const image = item.images?.[0] || getProductImageUrl(String(item.id)) || getFallbackImageUrl()

                return (
                  <div key={item.id} className="rounded-lg border border-gray-200 bg-white p-4">
                    <div className="flex gap-4">
                      <Link to={`/product/${item.id}`}>
                        <img src={image} alt={item.name} className="h-24 w-24 rounded-lg object-cover" />
                      </Link>

                      <div className="flex-1">
                        <Link to={`/product/${item.id}`}>
                          <h3 className="mb-1 font-semibold text-gray-900 hover:text-primary-600">
                            {item.name}
                          </h3>
                        </Link>
                        {item.description && (
                          <p className="mb-2 line-clamp-2 text-sm text-gray-600">{item.description}</p>
                        )}

                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => handleUpdateQuantity(item.articleId, item.qty - 1)}
                            disabled={mutating || item.qty <= 1}
                            className="rounded-md border border-gray-300 p-1 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <Minus className="h-4 w-4" />
                          </button>
                          <span className="w-8 text-center font-medium">{item.qty}</span>
                          <button
                            onClick={() => handleUpdateQuantity(item.articleId, item.qty + 1)}
                            disabled={mutating}
                            className="rounded-md border border-gray-300 p-1 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <Plus className="h-4 w-4" />
                          </button>
                        </div>
                      </div>

                      <div className="flex flex-col items-end justify-between">
                        <button
                          onClick={() => setItemToDelete({ id: item.articleId, name: item.name })}
                          disabled={mutating}
                          className="text-gray-400 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                        <div className="text-right">
                          <p className="text-sm text-gray-500">${item.price.toFixed(2)} c/u</p>
                          <p className="text-xl font-bold text-primary-600">
                            ${(item.price * item.qty).toFixed(2)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="lg:col-span-1">
              <div className="sticky top-4 rounded-lg border border-gray-200 bg-white p-6">
                <h2 className="mb-4 text-xl font-bold text-gray-900">Resumen</h2>

                <div className="mb-4 space-y-3 border-b border-gray-200 pb-4">
                  <div className="flex justify-between text-gray-600">
                    <span>Productos ({count})</span>
                    <span>${total.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-600">
                    <span>Envío</span>
                    <span className="text-green-600">Gratis</span>
                  </div>
                </div>

                <div className="mb-6 flex justify-between text-xl font-bold text-gray-900">
                  <span>Total</span>
                  <span className="text-primary-600">${total.toFixed(2)}</span>
                </div>

                <Link
                  to="/checkout"
                  className="mb-3 flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-primary-700"
                >
                  Proceder al Pago
                  <ArrowRight className="h-5 w-5" />
                </Link>

                <Link
                  to="/products"
                  className="block w-full rounded-lg border border-gray-300 bg-white px-6 py-3 text-center font-semibold text-gray-700 transition-colors hover:bg-gray-50"
                >
                  Seguir Comprando
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dialog para eliminar un producto */}
      <AlertDialog open={!!itemToDelete} onOpenChange={(open) => !open && setItemToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar producto</AlertDialogTitle>
            <AlertDialogDescription>
              ¿Estás seguro de que deseas eliminar <span className="font-medium text-gray-900">"{itemToDelete?.name}"</span> de tu carrito?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemove}
              className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-600"
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog para vaciar el carrito */}
      <AlertDialog open={showClearDialog} onOpenChange={setShowClearDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Vaciar carrito</AlertDialogTitle>
            <AlertDialogDescription>
              ¿Estás seguro de que deseas eliminar todos los productos de tu carrito? Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleClear}
              className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-600"
            >
              Vaciar carrito
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
