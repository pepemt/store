import { config } from '../config/api'

interface CartItem {
  article_id: string
  quantity: number
  [key: string]: unknown
}

interface Cart {
  items: CartItem[]
  total?: number
  [key: string]: unknown
}

interface CartResponse {
  ok?: boolean
  message?: string
  [key: string]: unknown
}

async function parseOrThrow(response: Response): Promise<any> {
  let data = null
  try {
    data = await response.json()
  } catch {
    // sin cuerpo JSON
  }
  if (!response.ok) {
    const msg = (data && (data.detail || data.message)) || `HTTP ${response.status} ${response.statusText}`
    throw new Error(msg)
  }
  return data
}

export const cartService = {
  async addToCart(customerId: string, articleId: string, quantity = 1): Promise<CartResponse> {
    const params = new URLSearchParams({
      customer_id: String(customerId),
      article_id: String(articleId),
      quantity: String(quantity),
    })

    const url = `${config.CART_URL}/add?${params.toString()}`
    const resp = await fetch(url, { method: 'POST' })
    return parseOrThrow(resp)
  },

  async getCart(customerId: string): Promise<Cart> {
    const url = `${config.CART_URL}/${encodeURIComponent(customerId)}`
    const resp = await fetch(url, { method: 'GET' })
    return parseOrThrow(resp)
  },

  async updateCartItem(customerId: string, articleId: string, newQuantity: number): Promise<CartResponse> {
    if (newQuantity < 0) {
      throw new Error('La cantidad no puede ser negativa')
    }

    const cart = await this.getCart(customerId)
    const current = (cart.items || []).find(i => Number(i.article_id) === Number(articleId))
    const currentQty = current ? Number(current.quantity) : 0

    if (newQuantity === currentQty) {
      return { ok: true, message: 'Cantidad sin cambios' }
    }

    if (newQuantity === 0 && currentQty > 0) {
      return this.removeFromCart(customerId, articleId, currentQty)
    }

    if (newQuantity > currentQty) {
      const delta = newQuantity - currentQty
      return this.addToCart(customerId, articleId, delta)
    } else {
      const delta = currentQty - newQuantity
      return this.removeFromCart(customerId, articleId, delta)
    }
  },

  async removeFromCart(customerId: string, articleId: string, quantity = 1): Promise<CartResponse> {
    const params = new URLSearchParams({
      customer_id: String(customerId),
      article_id: String(articleId),
      quantity: String(quantity),
    })

    const url = `${config.CART_URL}/remove?${params.toString()}`
    const resp = await fetch(url, { method: 'DELETE' })
    return parseOrThrow(resp)
  },

  async clearCart(customerId: string): Promise<CartResponse> {
    const cart = await this.getCart(customerId)
    const items = cart.items || []
    for (const it of items) {
      const qty = Number(it.quantity) || 0
      if (qty > 0) {
        await this.removeFromCart(customerId, it.article_id, qty)
      }
    }
    return { ok: true }
  },

  async getCartCount(customerId: string): Promise<number> {
    const url = `${config.CART_URL}/count/${encodeURIComponent(customerId)}`
    const resp = await fetch(url, { method: 'GET' })
    const data = await parseOrThrow(resp)
    return data.total_items || 0
  },
}

export default cartService
