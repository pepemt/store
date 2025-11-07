import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
} from 'react'
import { useAuth } from './AuthContext'
import { cartService } from '../services/cartService'
import { productService } from '../services/productService'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'

const CartContext = createContext()

const buildImageList = (productId, images = []) => {
  if (images?.length) return images
  const fallback = getProductImageUrl(productId) || getFallbackImageUrl()
  return fallback ? [fallback] : []
}

export const CartProvider = ({ children }) => {
  const { user } = useAuth()
  const customerId = user?.customer_id

  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [mutating, setMutating] = useState(false)

  const normalizeCartItem = useCallback(async (item) => {
    try {
      const product = await productService.getProductById(item.article_id)
      return {
        id: product.id,
        articleId: item.article_id,
        qty: item.quantity,
        name: product.name || item.article_name,
        description: product.description,
        price: product.price || 0,
        images: buildImageList(product.id, product.images),
        stock: product.stock,
        rating: product.rating,
        department: product.department,
      }
    } catch (err) {
      console.warn('No se pudo enriquecer item de carrito', err)
      return {
        id: item.article_id,
        articleId: item.article_id,
        qty: item.quantity,
        name: item.article_name || 'Producto',
        description: '',
        price: 0,
        images: buildImageList(item.article_id),
      }
    }
  }, [])

  const loadCart = useCallback(async () => {
    if (!customerId) {
      setItems([])
      setLoading(false)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const summary = await cartService.getCart(customerId)
      const enriched = await Promise.all(
        (summary.items || []).map(normalizeCartItem)
      )
      setItems(enriched)
    } catch (err) {
      console.error('Error al cargar carrito:', err)
      setItems([])
      setError(err.message || 'No se pudo cargar el carrito.')
    } finally {
      setLoading(false)
    }
  }, [customerId, normalizeCartItem])

  useEffect(() => {
    loadCart()
  }, [loadCart])

  const ensureAuth = () => {
    if (!customerId) {
      throw new Error('Debes iniciar sesión para usar el carrito.')
    }
  }

  const withMutation = async (fn) => {
    setMutating(true)
    setError(null)
    try {
      await fn()
      await loadCart()
    } catch (err) {
      console.error('Accion del carrito fallida:', err)
      setError(err.message || 'No se pudo actualizar el carrito.')
      throw err
    } finally {
      setMutating(false)
    }
  }

  const add = async (product, qty = 1) => {
    ensureAuth()
    if (!product?.id) {
      throw new Error('Producto inválido para carrito.')
    }
    await withMutation(() =>
      cartService.addToCart(customerId, product.id, qty)
    )
  }

  const updateQty = async (id, qty) => {
    ensureAuth()
    const safeQty = Math.max(0, Number(qty) || 0)
    await withMutation(() =>
      cartService.updateCartItem(customerId, id, safeQty)
    )
  }

  const remove = async (id) => {
    ensureAuth()
    await withMutation(() => cartService.removeFromCart(customerId, id))
  }

  const clear = async () => {
    ensureAuth()
    await withMutation(() => cartService.clearCart(customerId))
  }

  const total = useMemo(
    () => items.reduce((sum, item) => sum + (item.price || 0) * (item.qty || 0), 0),
    [items]
  )

  const count = useMemo(
    () => items.reduce((sum, item) => sum + (item.qty || 0), 0),
    [items]
  )

  return (
    <CartContext.Provider
      value={{
        items,
        add,
        remove,
        updateQty,
        clear,
        total,
        count,
        loading,
        error,
        mutating,
        refresh: loadCart,
        hasItems: items.length > 0,
      }}
    >
      {children}
    </CartContext.Provider>
  )
}

export const useCart = () => useContext(CartContext)
export default CartContext
