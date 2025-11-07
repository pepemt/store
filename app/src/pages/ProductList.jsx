  import React, { useState, useMemo, useEffect } from 'react'
  import { Link, useSearchParams } from 'react-router-dom'
  import { productService } from '../services/productService'
  import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
  import '../styles/ProductList.css'

  export default function ProductList() {
    const [searchParams, setSearchParams] = useSearchParams()
    const [products, setProducts] = useState([])
    const [categories, setCategories] = useState(['Todos'])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const qParam = searchParams.get('q') || ''
    const categoryParam = searchParams.get('category') || 'Todos'
    const [q, setQ] = useState(qParam)
    const [category, setCategory] = useState(categoryParam)

    // Actualizar URL cuando cambia la búsqueda o categoría
    useEffect(() => {
      const params = {}
      if (q.trim()) params.q = q.trim()
      if (category !== 'Todos') params.category = category
      setSearchParams(params)
    }, [q, category])

  // Cargar categorías al montar
    useEffect(() => {
      async function fetchCategories() {
        try {
          const cats = await productService.getCategories()
          setCategories(['Todos', ...cats])
        } catch (err) {
          console.error(err)
        }
      }
      fetchCategories()
    }, [])

    // Cargar productos cuando cambian filtros
    useEffect(() => {
      async function fetchProducts() {
        setLoading(true)
        setError(null)
        try {
          const data = await productService.getProducts({
            search: q || undefined,
            category: category === 'Todos' ? undefined : category,
            page: 1,
            per_page: 20,
          })
          // El backend devuelve { products, total, page, ... }
          setProducts(data.products || [])
        } catch (err) {
          console.error('Error al obtener productos:', err)
          setError('No se pudieron cargar los productos.')
        } finally {
          setLoading(false)
        }
      }
      fetchProducts()
    }, [q, category])

    
    if (loading) {
      return (
        <div className="products-page">
          <div className="loading-message">Cargando productos...</div>
        </div>
      )
    }

    if (error) {
      return (
        <div className="products-page">
          <div className="error-message">{error}</div>
        </div>
      )
    }

    return (
      <div className="products-page">
        <div className="products-header">
          <h1 className="products-title">Todos los productos</h1>
          <div className="products-controls">
            <div className="search-container">
              <input
                value={q}
                onChange={e => setQ(e.target.value)}
                placeholder="Buscar productos..."
                className="search-input"
              />
              <svg className="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="category-select"
            >
              <option>Todos</option>
              {categories.map(cat => <option key={cat}>{cat}</option>)}
            </select>
            <Link to="/cart" className="cart-button">
              🛒 Ver carrito
            </Link>
          </div>
        </div>

        <div className="products-grid">
          {products.map(p => (
            <div key={p.id} className="product-card">
              <Link to={`/product/${p.id}`}>
                <div className="product-image-container">
                  <img
                    src={p.images?.[0] || getProductImageUrl(p.id) || getFallbackImageUrl()}
                    alt={p.name || 'Producto'}
                    className="product-image"
                  />
                  {p.rating && (
                    <div className="product-badge">⭐ {p.rating}</div>
                  )}
                </div>
              </Link>
              <div className="product-content">
                <Link to={`/product/${p.id}`}>
                  <h3 className="product-title">{p.name}</h3>
                  <p className="product-description">{p.description}</p>
                </Link>
                <div className="product-footer">
                  <div className="product-price">
                    ${p.price ? p.price.toFixed(2) : '—'}
                  </div>
                  {typeof p.stock !== 'undefined' && (
                    <div className="product-stock">Stock: {p.stock}</div>
                  )}
                </div>
                <Link to={`/product/${p.id}`} className="view-button">
                  Ver detalles
                </Link>
              </div>
            </div>
          ))}

          {products.length === 0 && (
            <div className="no-products">
              <div className="no-products-icon">🔍</div>
              <h3 className="no-products-title">No encontramos productos</h3>
              <p className="no-products-text">
                Intenta con otros términos de búsqueda o cambia la categoría
              </p>
              <div className="search-suggestions">
                <span className="suggestion-tag" onClick={() => setQ('')}>Limpiar búsqueda</span>
                <span className="suggestion-tag" onClick={() => setCategory('Todos')}>Todas las categorías</span>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }
