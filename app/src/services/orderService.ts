import { config } from '../config/api'

export interface OrderItem {
  id: number
  article_id: number
  product_name: string
  quantity: number
  unit_price: number
  total_price: number
}

export interface Order {
  id: number
  status: string
  currency: string
  total_amount: number
  items_count: number
  created_at: string
  paid_at?: string
}

export interface OrderDetail {
  id: number
  status: string
  currency: string
  total_amount: number
  stripe_payment_intent_id?: string
  created_at: string
  updated_at: string
  paid_at?: string
  items: OrderItem[]
}

export interface OrderListResponse {
  orders: Order[]
  total: number
  limit: number
  offset: number
}

export interface GetOrdersParams {
  status?: string
  limit?: number
  offset?: number
}

export const orderService = {
  /**
   * Obtiene la lista de órdenes de un cliente
   */
  async getOrders(customerId: string, params?: GetOrdersParams): Promise<OrderListResponse> {
    const searchParams = new URLSearchParams()

    if (params?.status) searchParams.append('status', params.status)
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())

    const queryString = searchParams.toString()
    const url = `${config.ORDERS_URL}/${customerId}${queryString ? `?${queryString}` : ''}`

    const response = await fetch(url)

    if (!response.ok) {
      throw new Error('Error al obtener historial de pedidos')
    }

    return response.json()
  },

  /**
   * Obtiene el detalle de una orden específica
   */
  async getOrderById(customerId: string, orderId: number): Promise<OrderDetail> {
    const response = await fetch(`${config.ORDERS_URL}/${customerId}/${orderId}`)

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Pedido no encontrado')
      }
      throw new Error('Error al obtener detalle del pedido')
    }

    return response.json()
  },

  /**
   * Formatea el estado de una orden para mostrar
   */
  formatStatus(status: string): string {
    const statusMap: Record<string, string> = {
      pending: 'Pendiente',
      paid: 'Pagado',
      cancelled: 'Cancelado',
      refunded: 'Reembolsado',
    }
    return statusMap[status] || status
  },

  /**
   * Obtiene el color del badge según el estado
   */
  getStatusColor(status: string): string {
    const colorMap: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      paid: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      refunded: 'bg-gray-100 text-gray-800',
    }
    return colorMap[status] || 'bg-gray-100 text-gray-800'
  },
}

export default orderService
