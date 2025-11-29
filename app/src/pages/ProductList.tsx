import React, { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search, Star, ShoppingCart, Loader, Filter, X } from 'lucide-react'
import { useProducts, useCategories } from '../hooks/useProducts'
import { useCart } from '../context/CartContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import CachedImage from '../components/CachedImage'

interface Product {
  id: string | number
  name?: string
  title?: string
  description?: string
  price: number
  images?: string[]
  rating?: number
  stock?: number
  category?: string
  department?: string
}

export default function ProductList() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { add: addToCart } = useCart()

  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '')
  const [page, setPage] = useState(1)
  const selectedCategory = searchParams.get('category') || ''

  // Usar React Query para productos (con cache automático)
  const {
    data: productsData,
    isLoading: loading,
    error: productsError,
  } = useProducts({
    page,
    per_page: 12,
    search: searchParams.get('q') || undefined,
    category: selectedCategory || undefined,
  })

  // Usar React Query para categorías (cache de 1 hora)
  const {
    data: categories = [],
    isLoading: loadingCategories,
  } = useCategories()

  const products = productsData?.products || []
  const totalPages = productsData?.total_pages || 1
  const error = productsError ? 'Error al cargar productos' : ''

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const params: Record<string, string> = {}
    if (searchQuery.trim()) {
      params.q = searchQuery.trim()
    }
    if (selectedCategory) {
      params.category = selectedCategory
    }
    setSearchParams(params)
    setPage(1)
  }

  const handleCategoryChange = (category: string) => {
    const params: Record<string, string> = {}
    if (searchQuery.trim()) {
      params.q = searchQuery.trim()
    }
    if (category) {
      params.category = category
    }
    setSearchParams(params)
    setPage(1)
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSearchParams({})
    setPage(1)
  }

  const handleAddToCart = async (product: Product) => {
    try {
      await addToCart(product)
    } catch (err) {
      console.error('Error adding to cart:', err)
    }
  }

  return (
    <div className="bg-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header & Search */}
        <div className="mb-8">
          <h1 className="mb-6 text-3xl font-bold text-gray-900">Productos</h1>

          <form onSubmit={handleSearch} className="mb-4 flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar productos..."
                className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-4 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary-600 px-6 py-2.5 font-semibold text-white hover:bg-primary-700"
            >
              Buscar
            </button>
          </form>

          {/* Filtros por Categoría */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Filtrar por categoría:</span>
            </div>
            
            {loadingCategories ? (
              <div className="flex items-center gap-2">
                <Loader className="h-4 w-4 animate-spin text-gray-400" />
                <span className="text-sm text-gray-500">Cargando categorías...</span>
              </div>
            ) : (
              <>
                <button
                  onClick={() => handleCategoryChange('')}
                  className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    !selectedCategory
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Todas
                </button>
                {categories.map((category) => (
                  <button
                    key={category}
                    onClick={() => handleCategoryChange(category)}
                    className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                    style={{
                      backgroundColor: selectedCategory === category ? "#6e348d" : "#f3f4f6",
                      color: selectedCategory === category ? "white" : "#374151"
                    }}
                    onMouseEnter={(e) => {
                      if (selectedCategory !== category) {
                        e.currentTarget.style.backgroundColor = "#ffb320"
                        e.currentTarget.style.color = "white"
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (selectedCategory !== category) {
                        e.currentTarget.style.backgroundColor = "#f3f4f6"
                        e.currentTarget.style.color = "#374151"
                      }
                    }}
                  >
                    {category}
                  </button>
                ))}
                {(selectedCategory || searchQuery) && (
                  <button
                    onClick={clearFilters}
                    className="ml-auto flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    <X className="h-4 w-4" />
                    Limpiar filtros
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Results Info */}
        {(searchParams.get('q') || searchParams.get('category')) && (
          <div className="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm text-gray-600">
              {searchParams.get('q') && (
                <>Resultados de búsqueda para: <span className="font-semibold">{searchParams.get('q')}</span></>
              )}
              {searchParams.get('q') && searchParams.get('category') && ' • '}
              {searchParams.get('category') && (
                <>Categoría: <span className="font-semibold">{searchParams.get('category')}</span></>
              )}
            </p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Products Grid */}
        {!loading && !error && products.length > 0 && (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {products.map((product) => {
                const name = product.name || product.title || 'Producto'
                const image = product.images?.[0] || getProductImageUrl(String(product.id)) || getFallbackImageUrl()

                return (
                  <div
                    key={product.id}
                    className="group overflow-hidden rounded-lg border border-gray-200 bg-white transition-all hover:shadow-lg"
                  >
                    <Link to={`/product/${product.id}`}>
                      <div className="relative aspect-square overflow-hidden bg-gray-100">
                        <CachedImage
                          src={image}
                          alt={name}
                          fallbackSrc={getFallbackImageUrl()}
                          loading="lazy"
                          className="h-full w-full object-cover transition-transform group-hover:scale-110"
                        />
                        {product.rating && (
                          <div className="absolute right-2 top-2 flex items-center gap-1 rounded-md bg-white px-2 py-1 text-sm font-semibold shadow-sm">
                            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                            <span>{product.rating}</span>
                          </div>
                        )}
                      </div>
                    </Link>

                    <div className="p-4">
                      <Link to={`/product/${product.id}`}>
                        <h3 className="mb-2 line-clamp-2 font-semibold text-gray-900 hover:text-primary-600">
                          {name}
                        </h3>
                      </Link>

                      <p className="mb-3 line-clamp-2 text-sm text-gray-600">
                        {product.description}
                      </p>

                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-2xl font-bold text-primary-600">
                            ${product.price.toFixed(2)}
                          </span>
                        </div>

                        <button
                          onClick={() => handleAddToCart(product)}
                          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-white transition-colors"
                          style={{
                            backgroundColor: '#6e348d'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#ffb320'}
                          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#6e348d'}
                        >
                          <ShoppingCart className="h-4 w-4" />
                          Agregar
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex justify-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Anterior
                </button>

                <span className="flex items-center px-4 text-sm text-gray-600">
                  Página {page} de {totalPages}
                </span>

                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Siguiente
                </button>
              </div>
            )}
          </>
        )}

        {/* No Results */}
        {!loading && !error && products.length === 0 && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-12 text-center">
            <p className="text-lg font-medium text-gray-900">No se encontraron productos</p>
            <p className="mt-2 text-gray-600">Intenta con otros términos de búsqueda</p>
          </div>
        )}
      </div>
    </div>
  )
}
