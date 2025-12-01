import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Package, ChevronRight, ShoppingBag } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { orderService, Order } from '../services/orderService'

export default function Orders() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchOrders = async () => {
      const customerId = user?.customer_id || user?.id
      if (!customerId) {
        setError('Debes iniciar sesión para ver tus pedidos')
        setLoading(false)
        return
      }

      try {
        const response = await orderService.getOrders(customerId)
        setOrders(response.orders)
      } catch (err) {
        console.error('Error al cargar pedidos:', err)
        setError('Error al cargar el historial de pedidos')
      } finally {
        setLoading(false)
      }
    }

    fetchOrders()
  }, [user?.customer_id, user?.id])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          <p className="text-gray-600">Cargando pedidos...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="mb-4 text-red-600">{error}</p>
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

  if (orders.length === 0) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center bg-gray-50">
        <div className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-8 text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-gray-100">
            <Package className="h-12 w-12 text-gray-400" />
          </div>
          <h2 className="mb-3 text-2xl font-bold text-gray-900">Sin pedidos</h2>
          <p className="mb-6 text-gray-600">
            Aún no has realizado ningún pedido. ¡Explora nuestra tienda y encuentra algo que te guste!
          </p>
          <button
            onClick={() => navigate('/products')}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-medium text-white hover:bg-primary-700"
          >
            <ShoppingBag className="h-4 w-4" />
            Explorar productos
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-200px)] bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="mb-8 text-3xl font-bold text-gray-900">Mis Pedidos</h1>

        <div className="space-y-4">
          {orders.map((order) => (
            <div
              key={order.id}
              onClick={() => navigate(`/orders/${order.id}`)}
              className="cursor-pointer rounded-lg border border-gray-200 bg-white p-6 transition-shadow hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-100">
                    <Package className="h-6 w-6 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Pedido #{order.id}</p>
                    <p className="text-sm text-gray-500">{formatDate(order.created_at)}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <span
                      className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${orderService.getStatusColor(order.status)}`}
                    >
                      {orderService.formatStatus(order.status)}
                    </span>
                    <p className="mt-1 font-bold text-gray-900">
                      ${order.total_amount.toFixed(2)} {order.currency.toUpperCase()}
                    </p>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </div>
              </div>

              <div className="mt-4 border-t border-gray-100 pt-4">
                <p className="text-sm text-gray-500">
                  {order.items_count} {order.items_count === 1 ? 'producto' : 'productos'}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
