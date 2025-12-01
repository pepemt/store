import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Star, ShoppingCart, Package, Shield, Truck, Loader, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import { useProduct } from '../hooks/useProducts'
import { useCart } from '../context/CartContext'
import { productService } from '../services/productService'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import CachedImage from '../components/CachedImage'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'

interface SimilarProduct {
  id: string | number
  name?: string
  title?: string
  description?: string
  price: number
  images?: string[]
  rating?: number
}

export default function ProductDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { add: addToCart } = useCart()

  const [quantity, setQuantity] = useState(1)
  const [adding, setAdding] = useState(false)
  const [similarProducts, setSimilarProducts] = useState<SimilarProduct[]>([])
  const [similarLoading, setSimilarLoading] = useState(false)

  // Usar React Query para obtener producto (con cache de 10 minutos)
  const {
    data: product,
    isLoading: loading,
    error: productError,
  } = useProduct(id)

  const error = productError ? 'Producto no encontrado' : ''

  useEffect(() => {
    if (id) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      setQuantity(1) // Reset quantity when product changes
    }
  }, [id])

  // Cargar productos similares
  useEffect(() => {
    async function fetchSimilar() {
      if (!id) return

      try {
        setSimilarLoading(true)
        const products = await productService.getSimilarProducts(id, 4)
        setSimilarProducts(products)
      } catch (err) {
        console.error('Error al cargar productos similares:', err)
        setSimilarProducts([])
      } finally {
        setSimilarLoading(false)
      }
    }
    fetchSimilar()
  }, [id])

  const handleAddToCart = async () => {
    if (!product) return

    try {
      setAdding(true)
      await addToCart(product, quantity)
      toast.success('¡Producto agregado al carrito!', {
        description: `${quantity} ${quantity === 1 ? 'unidad' : 'unidades'} de ${name}`,
        duration: 3000,
      })
    } catch (err: any) {
      toast.error('Error al agregar al carrito', {
        description: err?.message || 'Por favor intenta nuevamente',
        duration: 4000,
      })
    } finally {
      setAdding(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-200px)] items-center justify-center">
        <Loader className="h-8 w-8 animate-spin" style={{ color: '#6e348d' }} />
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
          <AlertCircle className="mx-auto mb-4 h-12 w-12" style={{ color: '#dc2626' }} />
          <h2 className="mb-2 text-xl font-bold" style={{ color: '#7f1d1d' }}>{error}</h2>
          <button
            onClick={() => navigate('/products')}
            className="mt-4 rounded-lg px-6 py-2 font-semibold transition-colors"
            style={{ backgroundColor: '#6e348d', color: 'white' }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#5a2a72')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#6e348d')}
          >
            Ver todos los productos
          </button>
        </div>
      </div>
    )
  }

  const name = product.name || product.title || 'Producto'
  const image = product.images?.[0] || getProductImageUrl(String(product.id)) || getFallbackImageUrl()

  return (
    <div className="bg-white">
      <div className="container mx-auto px-4 py-8">
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-8">
            <CachedImage
              src={image}
              alt={name}
              fallbackSrc={getFallbackImageUrl()}
              loading="eager"
              className="w-full rounded-lg object-contain"
            />
          </div>

          <div>
            {product.category && (
              <p className="mb-2 text-sm font-medium" style={{ color: '#6e348d' }}>{product.category}</p>
            )}

            <h1 className="mb-4 text-3xl font-bold" style={{ color: '#111827' }}>{name}</h1>

            {product.rating && (
              <div className="mb-4 flex items-center gap-2">
                <div className="flex items-center gap-1">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`h-5 w-5 ${
                        i < Math.floor(product.rating!)
                          ? 'fill-yellow-400 text-yellow-400'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-sm" style={{ color: '#4b5563' }}>({product.rating})</span>
              </div>
            )}

            <div className="mb-6 flex items-baseline gap-3">
              <span className="text-4xl font-bold" style={{ color: '#6e348d' }}>${product.price.toFixed(2)}</span>
            </div>

            <p className="mb-6" style={{ color: '#374151' }}>{product.description}</p>

            <div className="mb-6">
              <label className="mb-2 block text-sm font-medium" style={{ color: '#374151' }}>Cantidad:</label>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="rounded-lg border border-gray-300 px-4 py-2 font-semibold hover:bg-gray-50"
                  style={{ color: '#374151' }}
                >
                  -
                </button>
                <span className="text-xl font-semibold" style={{ color: '#111827' }}>{quantity}</span>
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="rounded-lg border border-gray-300 px-4 py-2 font-semibold hover:bg-gray-50"
                  style={{ color: '#374151' }}
                >
                  +
                </button>
              </div>
            </div>

            <button
              onClick={handleAddToCart}
              disabled={adding}
              className="mb-6 flex w-full items-center justify-center gap-2 rounded-lg px-6 py-3 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                backgroundColor: adding ? '#ffb320' : '#6e348d',
                color: 'white'
              }}
              onMouseEnter={(e) => !adding && (e.currentTarget.style.backgroundColor = '#ffb320')}
              onMouseLeave={(e) => !adding && (e.currentTarget.style.backgroundColor = '#6e348d')}
            >
              {adding ? (
                <>
                  <Loader className="h-5 w-5 animate-spin" />
                  Agregando...
                </>
              ) : (
                <>
                  <ShoppingCart className="h-5 w-5" />
                  Agregar al Carrito
                </>
              )}
            </button>

            <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center gap-3 text-sm">
                <Truck className="h-5 w-5" style={{ color: '#4b5563' }} />
                <span style={{ color: '#374151' }}>Envío gratis en compras mayores a $500</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Shield className="h-5 w-5" style={{ color: '#4b5563' }} />
                <span style={{ color: '#374151' }}>Garantía de 30 días</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Package className="h-5 w-5" style={{ color: '#4b5563' }} />
                <span style={{ color: '#374151' }}>Envío en 24-48 horas</span>
              </div>
            </div>
          </div>
        </div>

        {/* Similar Products Section */}
        <section className="mt-16 border-t border-gray-200 pt-12">
          <h2 className="mb-8 text-2xl font-bold text-gray-900">Productos Similares</h2>

          {similarLoading ? (
            <div className="text-center py-8">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-r-transparent" style={{ borderColor: '#6e348d', borderRightColor: 'transparent' }}></div>
              <p className="mt-4 text-gray-600">Buscando productos similares...</p>
            </div>
          ) : similarProducts.length > 0 ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {similarProducts.map((p) => {
                const pName = p.name || p.title || 'Producto'
                const pImage = p.images?.[0] || getProductImageUrl(String(p.id)) || getFallbackImageUrl()
                return (
                  <Link
                    key={p.id}
                    to={`/product/${p.id}`}
                    className="group"
                  >
                    <Card className="overflow-hidden transition-shadow hover:shadow-lg">
                      <div className="relative aspect-square overflow-hidden bg-gray-100">
                        <img
                          src={pImage}
                          alt={pName}
                          className="h-full w-full object-cover transition-transform group-hover:scale-110"
                        />
                        {p.rating && (
                          <Badge className="absolute right-2 top-2 bg-white text-gray-900 hover:bg-white shadow-sm">
                            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400 mr-1" />
                            {p.rating}
                          </Badge>
                        )}
                      </div>
                      <CardHeader>
                        <CardTitle className="line-clamp-2 text-base">{pName}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="line-clamp-2 text-sm text-gray-600">
                          {p.description}
                        </p>
                      </CardContent>
                      <CardFooter>
                        <span className="text-xl font-bold" style={{ color: '#6e348d' }}>
                          ${p.price ? p.price.toFixed(2) : '0.00'}
                        </span>
                      </CardFooter>
                    </Card>
                  </Link>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">No se encontraron productos similares</p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
