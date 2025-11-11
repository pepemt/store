import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
  ReactNode,
} from 'react'
import { useAuth } from './AuthContext'
import { cartService } from '../services/cartService'
import { productService } from '../services/productService'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'

interface CartItem {
  id: string | number
  articleId: string | number
  qty: number
  name: string
  description?: string
  price: number
  images: string[]
  stock?: number
  rating?: number
  department?: string
}

interface Product {
  id: string | number
  name?: string
  title?: string
  description?: string
  price: number
  images?: string[]
  stock?: number
  rating?: number
  department?: string
}

interface CartContextType {
  items: CartItem[]
  add: (product: Product, qty?: number) => Promise<void>
  remove: (id: string | number) => Promise<void>
  updateQty: (id: string | number, qty: number) => Promise<void>
  clear: () => Promise<void>
  total: number
  count: number
  loading: boolean
  error: string | null
  mutating: boolean
  refresh: () => Promise<void>
  hasItems: boolean
}

const CartContext = createContext<CartContextType | undefined>(undefined)

const buildImageList = (productId: string | number, images: string[] = []): string[] => {
  if (images?.length) return images
  const fallback = getProductImageUrl(String(productId)) || getFallbackImageUrl()
  return fallback ? [fallback] : []
}

interface CartProviderProps {
  children: ReactNode
}

export const CartProvider: React.FC<CartProviderProps> = ({ children }) => {
  const { user } = useAuth()
  const customerId = user?.customer_id

  const [items, setItems] = useState<CartItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mutating, setMutating] = useState(false)

  const normalizeCartItem = useCallback(async (item: any): Promise<CartItem> => {
    try {
      const product = (await productService.getProductById(item.article_id)) as Product
      const images = Array.isArray(product.images) ? product.images : undefined
      return {
        id: product.id,
        articleId: item.article_id,
        qty: item.quantity,
        name: product.name || item.article_name,
        description: product.description,
        price: product.price || 0,
        images: buildImageList(product.id, images),
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
    } catch (err: any) {
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

  const ensureAuth = (): void => {
    if (!customerId) {
      throw new Error('Debes iniciar sesión para usar el carrito.')
    }
  }

  const withMutation = async (fn: () => Promise<any>): Promise<void> => {
    setMutating(true)
    setError(null)
    try {
      await fn()
      await loadCart()
    } catch (err: any) {
      console.error('Accion del carrito fallida:', err)
      setError(err.message || 'No se pudo actualizar el carrito.')
      throw err
    } finally {
      setMutating(false)
    }
  }

  const add = async (product: Product, qty = 1): Promise<void> => {
    ensureAuth()
    if (!product?.id) {
      throw new Error('Producto inválido para carrito.')
    }
    await withMutation(() =>
      cartService.addToCart(customerId!, String(product.id), qty)
    )
  }

  const updateQty = async (id: string | number, qty: number): Promise<void> => {
    ensureAuth()
    const safeQty = Math.max(0, Number(qty) || 0)
    await withMutation(() =>
      cartService.updateCartItem(customerId!, String(id), safeQty)
    )
  }

  const remove = async (id: string | number): Promise<void> => {
    ensureAuth()
    await withMutation(() => cartService.removeFromCart(customerId!, String(id)))
  }

  const clear = async (): Promise<void> => {
    ensureAuth()
    await withMutation(() => cartService.clearCart(customerId!))
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

export const useCart = (): CartContextType => {
  const context = useContext(CartContext)
  if (!context) {
    throw new Error('useCart debe usarse dentro de CartProvider')
  }
  return context
}

export default CartContext
