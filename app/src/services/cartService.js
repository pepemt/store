import { config } from '../config/api';

/**
 * Cart Service (frontend) — alineado con las rutas del backend:
 *  - POST   /api/v1/cart/add?customer_id=&article_id=&quantity=
 *  - GET    /api/v1/cart/{customer_id}
 *  - DELETE /api/v1/cart/remove?customer_id=&article_id=&quantity=
 *  - GET    /api/v1/cart/count/{customer_id}
 */

async function parseOrThrow(response) {
  // Intenta JSON; si falla, genera un error legible
  let data = null;
  try {
    data = await response.json();
  } catch {
    // sin cuerpo JSON
  }
  if (!response.ok) {
    const msg = (data && (data.detail || data.message)) || `HTTP ${response.status} ${response.statusText}`;
    throw new Error(msg);
  }
  return data;
}

export const cartService = {
  /**
   * Add item to cart
   * Backend espera query params (no body):
   *   POST /add?customer_id=&article_id=&quantity=
   */
  async addToCart(customerId, articleId, quantity = 1) {
    const params = new URLSearchParams({
      customer_id: String(customerId),
      article_id: String(articleId),
      quantity: String(quantity),
    });

    const url = `${config.CART_URL}/add?${params.toString()}`;
    const resp = await fetch(url, { method: 'POST' });
    return parseOrThrow(resp);
  },

  /**
   * Get full cart summary
   *   GET /{customer_id}
   */
  async getCart(customerId) {
    const url = `${config.CART_URL}/${encodeURIComponent(customerId)}`;
    const resp = await fetch(url, { method: 'GET' });
    return parseOrThrow(resp);
  },

  /**
   * Update item quantity (set exact quantity)
   * No hay endpoint dedicado en backend.
   * Estrategia: calculamos delta contra cantidad actual y usamos /add o /remove.
   */
  async updateCartItem(customerId, articleId, newQuantity) {
    if (newQuantity < 0) {
      throw new Error('La cantidad no puede ser negativa');
    }

    // 1) Obtener carrito para conocer la cantidad actual del item
    const cart = await this.getCart(customerId);
    const current = (cart.items || []).find(i => Number(i.article_id) === Number(articleId));
    const currentQty = current ? Number(current.quantity) : 0;

    if (newQuantity === currentQty) {
      return { ok: true, message: 'Cantidad sin cambios' };
    }

    if (newQuantity === 0 && currentQty > 0) {
      // eliminar todo el item de una
      return this.removeFromCart(customerId, articleId, currentQty);
    }

    if (newQuantity > currentQty) {
      // necesitamos agregar la diferencia
      const delta = newQuantity - currentQty;
      return this.addToCart(customerId, articleId, delta);
    } else {
      // necesitamos restar la diferencia
      const delta = currentQty - newQuantity;
      return this.removeFromCart(customerId, articleId, delta);
    }
  },

  /**
   * Remove / decrement item from cart
   *   DELETE /remove?customer_id=&article_id=&quantity=
   * Si la cantidad enviada >= cantidad en el carrito, el backend borra el ítem.
   */
  async removeFromCart(customerId, articleId, quantity = 1) {
    const params = new URLSearchParams({
      customer_id: String(customerId),
      article_id: String(articleId),
      quantity: String(quantity),
    });

    const url = `${config.CART_URL}/remove?${params.toString()}`;
    const resp = await fetch(url, { method: 'DELETE' });
    return parseOrThrow(resp);
  },

  /**
   * Clear entire cart (no endpoint dedicado en backend).
   * Implementación: traer items y eliminarlos con /remove.
   */
  async clearCart(customerId) {
    const cart = await this.getCart(customerId);
    const items = cart.items || [];
    for (const it of items) {
      const qty = Number(it.quantity) || 0;
      if (qty > 0) {
        await this.removeFromCart(customerId, it.article_id, qty);
      }
    }
    return { ok: true };
  },

  /**
   * Get cart item count
   *   GET /count/{customer_id}
   */
  async getCartCount(customerId) {
    const url = `${config.CART_URL}/count/${encodeURIComponent(customerId)}`;
    const resp = await fetch(url, { method: 'GET' });
    const data = await parseOrThrow(resp);
    return data.total_items || 0;
  },
};

export default cartService;
