import React, { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import cartService from '../services/cartService'

const CartContext = createContext()

export const CartProvider = ({ children }) => {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)

  // Load cart from API when user is authenticated
  useEffect(() => {
    if (user?.id) {
      loadCart()
    } else {
      // Fallback to local storage if not authenticated
      try {
        const localCart = JSON.parse(localStorage.getItem('tiendita_cart') || '[]')
        setItems(localCart)
      } catch {
        setItems([])
      }
    }
  }, [user?.id])

  const loadCart = async () => {
    if (!user?.id) return
    
    setLoading(true)
    try {
      const cartData = await cartService.getCart(user.id)
      // Transform API cart items to match frontend structure
      const transformedItems = cartData.items.map(item => ({
        id: item.article_id,
        qty: item.quantity,
        addedAt: item.added_at,
        name: item.article_name,
      }))
      setItems(transformedItems)
    } catch (error) {
      console.error('Error loading cart:', error)
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  const add = async (product, qty = 1) => {
    if (!user?.id) {
      // Fallback to local storage if not authenticated
      setItems(prev => {
        const idx = prev.findIndex(i => i.id === product.id)
        if (idx === -1) return [...prev, { ...product, qty }]
        const next = [...prev]
        next[idx].qty = Math.min((next[idx].qty || 0) + qty, product.stock || 9999)
        localStorage.setItem('tiendita_cart', JSON.stringify(next))
        return next
      })
      return
    }

    try {
      await cartService.addToCart(user.id, product.id, qty)
      await loadCart() // Reload cart from API
    } catch (error) {
      console.error('Error adding to cart:', error)
      throw error
    }
  }

  const remove = async (articleId) => {
    if (!user?.id) {
      // Fallback to local storage if not authenticated
      const updatedItems = items.filter(i => i.id !== articleId)
      setItems(updatedItems)
      localStorage.setItem('tiendita_cart', JSON.stringify(updatedItems))
      return
    }

    try {
      await cartService.removeFromCart(user.id, articleId)
      await loadCart() // Reload cart from API
    } catch (error) {
      console.error('Error removing from cart:', error)
      throw error
    }
  }

  const updateQty = async (articleId, qty) => {
    if (!user?.id) {
      // Fallback to local storage if not authenticated
      setItems(prev => {
        const updated = prev.map(i => i.id === articleId ? { ...i, qty: Math.max(1, qty) } : i)
        localStorage.setItem('tiendita_cart', JSON.stringify(updated))
        return updated
      })
      return
    }

    try {
      if (qty <= 0) {
        await cartService.removeFromCart(user.id, articleId)
      } else {
        await cartService.updateCartItem(user.id, articleId, qty)
      }
      await loadCart() // Reload cart from API
    } catch (error) {
      console.error('Error updating cart:', error)
      throw error
    }
  }

  const clear = async () => {
    if (!user?.id) {
      setItems([])
      localStorage.removeItem('tiendita_cart')
      return
    }

    try {
      await cartService.clearCart(user.id)
      setItems([])
    } catch (error) {
      console.error('Error clearing cart:', error)
      throw error
    }
  }

  const total = items.reduce((s, it) => s + (it.price || 0) * (it.qty || 0), 0)

  const count = items.reduce((s, it) => s + (it.qty || 0), 0)

  return (
    <CartContext.Provider value={{ items, add, remove, updateQty, clear, total, count, loading, loadCart }}>
      {children}
    </CartContext.Provider>
  )
}

export const useCart = () => useContext(CartContext)
export default CartContext
