import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle, Package, ArrowRight } from 'lucide-react'
import { useCart } from '../context/CartContext'
import { checkoutService, SessionStatusResponse } from '../services/checkoutService'

export default function CheckoutSuccess() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { refresh } = useCart()

  const [loading, setLoading] = useState(true)
  const [sessionStatus, setSessionStatus] = useState<SessionStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const sessionId = searchParams.get('session_id')

  useEffect(() => {
    const verifyPayment = async () => {
      if (!sessionId) {
        setError('No se encontró información del pago')
        setLoading(false)
        return
      }

      try {
        const status = await checkoutService.getSessionStatus(sessionId)
        setSessionStatus(status)

        // Refrescar el carrito (debería estar vacío ahora)
        await refresh()
      } catch (err) {
        console.error('Error verificando pago:', err)
        setError('Error al verificar el estado del pago')
      } finally {
        setLoading(false)
      }
    }

    verifyPayment()
  }, [sessionId, refresh])

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          <p className="text-gray-600">Verificando pago...</p>
        </div>
      </div>
    )
  }

  if (error || sessionStatus?.payment_status !== 'paid') {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
        <div className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-yellow-100">
            <Package className="h-12 w-12 text-yellow-600" />
          </div>
          <h2 className="mb-3 text-2xl font-bold text-gray-900">Verificando Pago</h2>
          <p className="mb-6 text-gray-600">
            {error || 'Tu pago está siendo procesado. Si el problema persiste, contacta soporte.'}
          </p>
          <button
            onClick={() => navigate('/')}
            className="rounded-lg bg-primary-600 px-6 py-2 font-medium text-white hover:bg-primary-700"
          >
            Ir al inicio
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
      <div className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
          <CheckCircle className="h-12 w-12 text-green-600" />
        </div>

        <h2 className="mb-3 text-2xl font-bold text-gray-900">¡Compra Exitosa!</h2>

        <p className="mb-6 text-gray-600">
          Tu pedido ha sido procesado correctamente. Recibirás un correo de confirmación con los detalles de tu compra.
        </p>

        {sessionStatus?.order_id && (
          <p className="mb-6 text-sm text-gray-500">
            Número de pedido: <span className="font-medium">#{sessionStatus.order_id}</span>
          </p>
        )}

        <div className="flex flex-col gap-3">
          <button
            onClick={() => navigate('/orders')}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-medium text-white hover:bg-primary-700"
          >
            Ver mis pedidos
            <ArrowRight className="h-4 w-4" />
          </button>

          <button
            onClick={() => navigate('/')}
            className="w-full rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50"
          >
            Seguir comprando
          </button>
        </div>
      </div>
    </div>
  )
}
