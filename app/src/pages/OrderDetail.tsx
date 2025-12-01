import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Package, ArrowLeft, CheckCircle, Clock, XCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { orderService, OrderDetail as OrderDetailType } from '../services/orderService'

export default function OrderDetail() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()

  const [order, setOrder] = useState<OrderDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchOrder = async () => {
      const customerId = user?.customer_id || user?.id
      if (!customerId || !id) {
        setError('Información de pedido no disponible')
        setLoading(false)
        return
      }

      try {
        const orderData = await orderService.getOrderById(customerId, parseInt(id))
        setOrder(orderData)
      } catch (err) {
        console.error('Error al cargar pedido:', err)
        setError('Error al cargar el detalle del pedido')
      } finally {
        setLoading(false)
      }
    }

    fetchOrder()
  }, [user?.customer_id, user?.id, id])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
        return <CheckCircle className="h-6 w-6 text-green-600" />
      case 'pending':
        return <Clock className="h-6 w-6 text-yellow-600" />
      case 'cancelled':
      case 'refunded':
        return <XCircle className="h-6 w-6 text-red-600" />
      default:
        return <Package className="h-6 w-6 text-gray-600" />
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          <p className="text-gray-600">Cargando pedido...</p>
        </div>
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="mb-4 text-red-600">{error || 'Pedido no encontrado'}</p>
          <button
            onClick={() => navigate('/orders')}
            className="rounded-lg bg-primary-600 px-6 py-2 font-medium text-white hover:bg-primary-700"
          >
            Volver a pedidos
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-200px)] bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/orders')}
            className="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver a mis pedidos
          </button>
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">Pedido #{order.id}</h1>
            <span
              className={`inline-block rounded-full px-4 py-2 text-sm font-medium ${orderService.getStatusColor(order.status)}`}
            >
              {orderService.formatStatus(order.status)}
            </span>
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Order Items */}
          <div className="lg:col-span-2">
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="mb-4 text-xl font-bold text-gray-900">Productos</h2>

              <div className="divide-y divide-gray-200">
                {order.items.map((item) => (
                  <div key={item.id} className="flex items-center gap-4 py-4">
                    <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-gray-100">
                      <Package className="h-8 w-8 text-gray-400" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">{item.product_name}</h3>
                      <p className="text-sm text-gray-500">
                        Cantidad: {item.quantity} x ${item.unit_price.toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-gray-900">${item.total_price.toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="sticky top-4 space-y-6">
              {/* Status Card */}
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                <div className="flex items-center gap-3">
                  {getStatusIcon(order.status)}
                  <div>
                    <h3 className="font-bold text-gray-900">
                      {orderService.formatStatus(order.status)}
                    </h3>
                    {order.paid_at && (
                      <p className="text-sm text-gray-500">Pagado el {formatDate(order.paid_at)}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Summary Card */}
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                <h2 className="mb-4 text-xl font-bold text-gray-900">Resumen</h2>

                <div className="space-y-3">
                  <div className="flex justify-between text-gray-600">
                    <span>Subtotal</span>
                    <span>${order.total_amount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-600">
                    <span>Envío</span>
                    <span className="text-green-600">Gratis</span>
                  </div>
                  <div className="border-t border-gray-200 pt-3">
                    <div className="flex justify-between text-lg font-bold text-gray-900">
                      <span>Total</span>
                      <span className="text-primary-600">
                        ${order.total_amount.toFixed(2)} {order.currency.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Details Card */}
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                <h2 className="mb-4 text-xl font-bold text-gray-900">Detalles</h2>

                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Fecha de pedido</span>
                    <span className="text-gray-900">{formatDate(order.created_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Número de pedido</span>
                    <span className="text-gray-900">#{order.id}</span>
                  </div>
                  {order.stripe_payment_intent_id && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">ID de pago</span>
                      <span className="truncate text-gray-900 max-w-[150px]" title={order.stripe_payment_intent_id}>
                        {order.stripe_payment_intent_id.slice(0, 20)}...
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
