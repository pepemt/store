import React, { useState, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search, Star, ShoppingCart, Loader, SlidersHorizontal, X } from 'lucide-react'
import { useProducts, useFilterOptions } from '../hooks/useProducts'
import { useCart } from '../context/CartContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import CachedImage from '../components/CachedImage'
import FilterSidebar from '../components/FilterSidebar'

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
  const [showFilters, setShowFilters] = useState(false)

  // Extraer filtros de URL
  const activeFilters = useMemo(() => ({
    category: searchParams.get('category') || undefined,
    color_group: searchParams.get('color_group') || undefined,
    product_type: searchParams.get('product_type') || undefined,
    price_min: searchParams.get('price_min') ? Number(searchParams.get('price_min')) : undefined,
    price_max: searchParams.get('price_max') ? Number(searchParams.get('price_max')) : undefined,
  }), [searchParams])

  // Usar React Query para productos
  const {
    data: productsData,
    isLoading: loading,
    error: productsError,
  } = useProducts({
    page,
    per_page: 12,
    search: searchParams.get('q') || undefined,
    ...activeFilters,
  })

  // Usar React Query para opciones de filtros
  const {
    data: filterOptions,
    isLoading: loadingFilters,
  } = useFilterOptions()

  const products = productsData?.products || []
  const totalPages = productsData?.total_pages || 1
  const error = productsError ? 'Error al cargar productos' : ''

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (searchQuery.trim()) {
      params.set('q', searchQuery.trim())
    } else {
      params.delete('q')
    }
    setSearchParams(params)
    setPage(1)
  }

  const handleFilterChange = (filters: typeof activeFilters) => {
    const params = new URLSearchParams()
    const q = searchParams.get('q')
    if (q) params.set('q', q)

    if (filters.category) params.set('category', filters.category)
    if (filters.color_group) params.set('color_group', filters.color_group)
    if (filters.product_type) params.set('product_type', filters.product_type)
    if (filters.price_min !== undefined) params.set('price_min', filters.price_min.toString())
    if (filters.price_max !== undefined) params.set('price_max', filters.price_max.toString())

    setSearchParams(params)
    setPage(1)
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSearchParams({})
    setPage(1)
  }

  const activeFilterCount = Object.values(activeFilters).filter((v) => v !== undefined).length

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
        <div className="mb-6">
          <h1 className="mb-4 text-3xl font-bold text-gray-900">Productos</h1>

          <div className="flex gap-2 sm:gap-3">
            <form onSubmit={handleSearch} className="flex flex-1 gap-2 sm:gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar..."
                  className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-4 focus:border-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-600"
                />
              </div>
              <button
                type="submit"
                className="hidden rounded-lg px-6 py-2.5 font-semibold text-white sm:block"
                style={{ backgroundColor: '#6e348d' }}
              >
                Buscar
              </button>
            </form>

            {/* Toggle filtros en móvil */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2.5 font-medium text-gray-700 hover:bg-gray-50 lg:hidden"
            >
              <SlidersHorizontal className="h-5 w-5" />
              <span className="hidden sm:inline">Filtros</span>
              {activeFilterCount > 0 && (
                <span
                  className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
                  style={{ backgroundColor: '#6e348d' }}
                >
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Results Info */}
        {(searchParams.get('q') || activeFilterCount > 0) && (
          <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 sm:px-4 sm:py-3">
            <span className="text-xs text-gray-600 sm:text-sm">Filtros:</span>
            {searchParams.get('q') && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800">
                {searchParams.get('q')}
              </span>
            )}
            {activeFilters.category && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800">
                {activeFilters.category}
              </span>
            )}
            {activeFilters.color_group && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800">
                {activeFilters.color_group}
              </span>
            )}
            {activeFilters.product_type && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800">
                {activeFilters.product_type}
              </span>
            )}
            {(activeFilters.price_min !== undefined || activeFilters.price_max !== undefined) && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800">
                ${activeFilters.price_min ?? 0} - ${activeFilters.price_max ?? '...'}
              </span>
            )}
            <button
              onClick={clearFilters}
              className="ml-auto flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 sm:text-sm"
            >
              <X className="h-3 w-3 sm:h-4 sm:w-4" />
              Limpiar
            </button>
          </div>
        )}

        {/* Mobile filter overlay */}
        {showFilters && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setShowFilters(false)} />
            <div className="absolute bottom-0 left-0 right-0 max-h-[80vh] overflow-y-auto rounded-t-2xl bg-white p-4">
              <FilterSidebar
                filterOptions={filterOptions}
                isLoading={loadingFilters}
                activeFilters={activeFilters}
                onFilterChange={handleFilterChange}
                onClearFilters={clearFilters}
                onClose={() => setShowFilters(false)}
              />
            </div>
          </div>
        )}

        {/* Main content with sidebar */}
        <div className="flex gap-6">
          {/* Filtros Sidebar - Solo desktop */}
          <aside className="hidden w-64 flex-shrink-0 lg:block">
            <FilterSidebar
              filterOptions={filterOptions}
              isLoading={loadingFilters}
              activeFilters={activeFilters}
              onFilterChange={handleFilterChange}
              onClearFilters={clearFilters}
            />
          </aside>

          {/* Products area */}
          <div className="min-w-0 flex-1">

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
            <p className="mt-2 text-gray-600">Intenta con otros términos de búsqueda o ajusta los filtros</p>
          </div>
        )}
          </div>
        </div>
      </div>
    </div>
  )
}
