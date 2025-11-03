import { config } from '../config/api';

/**
 * Cart Service
 * Handles cart operations (add, remove, update, get)
 */

export const cartService = {
  /**
   * Add item to cart
   * @param {string} customerId - Customer ID
   * @param {number} articleId - Article/Product ID
   * @param {number} quantity - Quantity to add (default: 1)
   * @returns {Promise<Object>} Cart item data
   */
  async addToCart(customerId, articleId, quantity = 1) {
    try {
      const response = await fetch(`${config.CART_URL}/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          customer_id: customerId,
          article_id: articleId,
          quantity,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al agregar al carrito');
      }

      return data;
    } catch (error) {
      console.error('Error al agregar al carrito:', error);
      throw error;
    }
  },

  /**
   * Get cart contents
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} Cart summary with items
   */
  async getCart(customerId) {
    try {
      const response = await fetch(`${config.CART_URL}/${customerId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener el carrito');
      }

      return data;
    } catch (error) {
      console.error('Error al obtener el carrito:', error);
      throw error;
    }
  },

  /**
   * Update item quantity in cart
   * @param {string} customerId - Customer ID
   * @param {number} articleId - Article ID
   * @param {number} quantity - New quantity (0 to remove)
   * @returns {Promise<Object>} Success message
   */
  async updateCartItem(customerId, articleId, quantity) {
    try {
      const params = new URLSearchParams({ quantity: quantity.toString() });
      
      const response = await fetch(
        `${config.CART_URL}/item/${customerId}/${articleId}?${params.toString()}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al actualizar el carrito');
      }

      return data;
    } catch (error) {
      console.error('Error al actualizar el carrito:', error);
      throw error;
    }
  },

  /**
   * Remove item from cart
   * @param {string} customerId - Customer ID
   * @param {number} articleId - Article ID
   * @returns {Promise<Object>} Success message
   */
  async removeFromCart(customerId, articleId) {
    try {
      const response = await fetch(
        `${config.CART_URL}/item/${customerId}/${articleId}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al eliminar del carrito');
      }

      return data;
    } catch (error) {
      console.error('Error al eliminar del carrito:', error);
      throw error;
    }
  },

  /**
   * Clear entire cart
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} Success message
   */
  async clearCart(customerId) {
    try {
      const response = await fetch(`${config.CART_URL}/clear/${customerId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al vaciar el carrito');
      }

      return data;
    } catch (error) {
      console.error('Error al vaciar el carrito:', error);
      throw error;
    }
  },

  /**
   * Get cart item count
   * @param {string} customerId - Customer ID
   * @returns {Promise<number>} Total item count
   */
  async getCartCount(customerId) {
    try {
      const response = await fetch(`${config.CART_URL}/count/${customerId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener el conteo del carrito');
      }

      return data.total_items || 0;
    } catch (error) {
      console.error('Error al obtener el conteo del carrito:', error);
      throw error;
    }
  },
};

export default cartService;

