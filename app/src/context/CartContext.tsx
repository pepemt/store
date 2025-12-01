import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
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

  // Cache de productos para evitar llamadas repetidas
  const productCache = useRef<Map<string, Product>>(new Map())

  const getProductCached = useCallback(async (articleId: string): Promise<Product | null> => {
    if (productCache.current.has(articleId)) {
      return productCache.current.get(articleId)!
    }
    try {
      const product = await productService.getProductById(articleId) as Product
      productCache.current.set(articleId, product)
      return product
    } catch {
      return null
    }
  }, [])

  const normalizeCartItem = useCallback(async (item: any): Promise<CartItem> => {
    const product = await getProductCached(item.article_id)

    if (product) {
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
    }

    return {
      id: item.article_id,
      articleId: item.article_id,
      qty: item.quantity,
      name: item.article_name || 'Producto',
      description: '',
      price: 0,
      images: buildImageList(item.article_id),
    }
  }, [getProductCached])

  const loadCart = useCallback(async (showLoading = true) => {
    if (!customerId) {
      setItems([])
      setLoading(false)
      setError(null)
      return
    }

    if (showLoading) setLoading(true)
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

  // Actualización optimista de cantidad
  const updateQty = useCallback(async (id: string | number, qty: number): Promise<void> => {
    ensureAuth()
    const safeQty = Math.max(0, Number(qty) || 0)
    const articleId = String(id)

    // Guardar estado anterior para rollback
    const previousItems = [...items]

    // Si qty es 0, eliminar el item
    if (safeQty === 0) {
      setItems(prev => prev.filter(item => String(item.articleId) !== articleId))
    } else {
      // Actualización optimista inmediata
      setItems(prev => prev.map(item =>
        String(item.articleId) === articleId
          ? { ...item, qty: safeQty }
          : item
      ))
    }

    setMutating(true)
    setError(null)

    try {
      await cartService.updateCartItem(customerId!, articleId, safeQty)
    } catch (err: any) {
      // Rollback en caso de error
      setItems(previousItems)
      setError(err.message || 'No se pudo actualizar el carrito.')
      throw err
    } finally {
      setMutating(false)
    }
  }, [customerId, items])

  // Agregar producto con actualización optimista
  const add = useCallback(async (product: Product, qty = 1): Promise<void> => {
    ensureAuth()
    if (!product?.id) {
      throw new Error('Producto inválido para carrito.')
    }

    const articleId = String(product.id)
    const previousItems = [...items]

    // Actualización optimista
    setItems(prev => {
      const existingIndex = prev.findIndex(item => String(item.articleId) === articleId)

      if (existingIndex >= 0) {
        // Incrementar cantidad si ya existe
        return prev.map((item, idx) =>
          idx === existingIndex
            ? { ...item, qty: item.qty + qty }
            : item
        )
      }

      // Agregar nuevo item
      const images = Array.isArray(product.images) ? product.images : undefined
      const newItem: CartItem = {
        id: product.id,
        articleId: product.id,
        qty,
        name: product.name || product.title || 'Producto',
        description: product.description,
        price: product.price || 0,
        images: buildImageList(product.id, images),
        stock: product.stock,
        rating: product.rating,
        department: product.department,
      }
      return [...prev, newItem]
    })

    // Cachear producto
    productCache.current.set(articleId, product)

    setMutating(true)
    setError(null)

    try {
      await cartService.addToCart(customerId!, articleId, qty)
    } catch (err: any) {
      setItems(previousItems)
      setError(err.message || 'No se pudo agregar al carrito.')
      throw err
    } finally {
      setMutating(false)
    }
  }, [customerId, items])

  // Eliminar con actualización optimista
  const remove = useCallback(async (id: string | number): Promise<void> => {
    ensureAuth()
    const articleId = String(id)
    const previousItems = [...items]

    // Buscar el item para obtener la cantidad total a eliminar
    const itemToRemove = items.find(item => String(item.articleId) === articleId)
    const qtyToRemove = itemToRemove?.qty || 1

    // Actualización optimista
    setItems(prev => prev.filter(item => String(item.articleId) !== articleId))

    setMutating(true)
    setError(null)

    try {
      await cartService.removeFromCart(customerId!, articleId, qtyToRemove)
    } catch (err: any) {
      setItems(previousItems)
      setError(err.message || 'No se pudo eliminar del carrito.')
      throw err
    } finally {
      setMutating(false)
    }
  }, [customerId, items])

  // Limpiar carrito con actualización optimista
  const clear = useCallback(async (): Promise<void> => {
    ensureAuth()
    const previousItems = [...items]

    // Actualización optimista
    setItems([])

    setMutating(true)
    setError(null)

    try {
      await cartService.clearCart(customerId!)
    } catch (err: any) {
      setItems(previousItems)
      setError(err.message || 'No se pudo vaciar el carrito.')
      throw err
    } finally {
      setMutating(false)
    }
  }, [customerId, items])

  const total = useMemo(
    () => items.reduce((sum, item) => sum + (item.price || 0) * (item.qty || 0), 0),
    [items]
  )

  const count = useMemo(
    () => items.reduce((sum, item) => sum + (item.qty || 0), 0),
    [items]
  )

  const contextValue = useMemo(() => ({
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
  }), [items, add, remove, updateQty, clear, total, count, loading, error, mutating, loadCart])

  return (
    <CartContext.Provider value={contextValue}>
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
