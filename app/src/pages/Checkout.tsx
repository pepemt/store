import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CreditCard, ShoppingBag, Lock, ArrowLeft } from 'lucide-react'
import { useCart } from '../context/CartContext'
import { useAuth } from '../context/AuthContext'
import { checkoutService } from '../services/checkoutService'

export default function Checkout() {
  const navigate = useNavigate()
  const { items, total, hasItems } = useCart()
  const { user } = useAuth()

  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCheckout = async () => {
    const customerId = user?.customer_id || user?.id
    if (!customerId) {
      setError('Debes iniciar sesión para continuar')
      return
    }

    setProcessing(true)
    setError(null)

    try {
      // Crear sesión de Stripe Checkout
      const result = await checkoutService.createSession(customerId)

      // Redirigir a Stripe Checkout
      checkoutService.redirectToCheckout(result.checkout_url)
    } catch (err) {
      console.error('Error al procesar pago:', err)
      setError(err instanceof Error ? err.message : 'Error al procesar el pago')
      setProcessing(false)
    }
  }

  // Redirigir si el carrito está vacío
  if (!hasItems) {
    navigate('/cart')
    return null
  }

  return (
    <div className="min-h-[calc(100vh-200px)] bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/cart')}
            className="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver al carrito
          </button>
          <h1 className="text-3xl font-bold text-gray-900">Finalizar Compra</h1>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Order Summary */}
          <div className="lg:col-span-2">
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <div className="mb-4 flex items-center gap-2">
                <ShoppingBag className="h-5 w-5 text-primary-600" />
                <h2 className="text-xl font-bold text-gray-900">Resumen del Pedido</h2>
              </div>

              <div className="divide-y divide-gray-200">
                {items.map((item) => (
                  <div key={item.id} className="flex items-center gap-4 py-4">
                    <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
                      {item.images?.[0] ? (
                        <img
                          src={item.images[0]}
                          alt={item.name}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center">
                          <ShoppingBag className="h-6 w-6 text-gray-400" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">{item.name}</h3>
                      <p className="text-sm text-gray-500">Cantidad: {item.qty}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-gray-900">
                        ${(item.price * item.qty).toFixed(2)}
                      </p>
                      <p className="text-sm text-gray-500">${item.price.toFixed(2)} c/u</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Payment Info */}
            <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
              <div className="mb-4 flex items-center gap-2">
                <Lock className="h-5 w-5 text-green-600" />
                <h2 className="text-xl font-bold text-gray-900">Pago Seguro</h2>
              </div>

              <p className="text-gray-600">
                Serás redirigido a la página de pago segura de Stripe para completar tu compra.
                Aceptamos las principales tarjetas de crédito y débito.
              </p>

              <div className="mt-4 flex items-center gap-3">
                <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/visa.svg" alt="Visa" className="h-8 w-auto opacity-60" />
                <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/mastercard.svg" alt="Mastercard" className="h-8 w-auto opacity-60" />
                <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/americanexpress.svg" alt="Amex" className="h-8 w-auto opacity-60" />
              </div>
            </div>
          </div>

          {/* Checkout Button */}
          <div className="lg:col-span-1">
            <div className="sticky top-4 rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 text-xl font-bold text-gray-900">Total a Pagar</h2>

              <div className="mb-4 space-y-2 border-b border-gray-200 pb-4">
                <div className="flex justify-between text-gray-600">
                  <span>Subtotal ({items.length} productos)</span>
                  <span>${total.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-gray-600">
                  <span>Envío</span>
                  <span className="text-green-600">Gratis</span>
                </div>
              </div>

              <div className="mb-6 flex justify-between text-xl font-bold text-gray-900">
                <span>Total</span>
                <span className="text-primary-600">${total.toFixed(2)} USD</span>
              </div>

              {error && (
                <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
                  {error}
                </div>
              )}

              <button
                onClick={handleCheckout}
                disabled={processing}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {processing ? (
                  <>
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Procesando...
                  </>
                ) : (
                  <>
                    <CreditCard className="h-5 w-5" />
                    Pagar con Stripe
                  </>
                )}
              </button>

              <p className="mt-4 text-center text-xs text-gray-500">
                Al continuar, aceptas nuestros términos y condiciones.
                Tu información de pago está protegida por Stripe.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
