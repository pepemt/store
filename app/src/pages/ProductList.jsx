import React, { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import productService from '../services/productService'
import '../styles/ProductList.css'

export default function ProductList() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  // Load categories from API
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const cats = await productService.getCategories()
        setCategories(['Todos', ...cats])
      } catch (error) {
        console.error('Error loading categories:', error)
        setCategories(['Todos'])
      }
    }
    loadCategories()
  }, [])

  // Load products from API
  useEffect(() => {
    const loadProducts = async () => {
      setLoading(true)
      try {
        console.log('Loading products with:', { page, q, category })
        const data = await productService.getProducts({
          page,
          per_page: 20,
          search: q || undefined,
          category: category && category !== 'Todos' ? category : undefined,
        })
        console.log('Products loaded:', data)
        setProducts(data.products || [])
        setTotalPages(data.total_pages || 1)
      } catch (error) {
        console.error('Error loading products:', error)
        setProducts([])
      } finally {
        setLoading(false)
      }
    }
    loadProducts()
  }, [page, q, category])

  return (
    <div className="products-page">
      <div className="products-header">
        <h1 className="products-title">Todos los productos</h1>
        <div className="products-controls">
          <div className="search-container">
            <input
              value={q}
              onChange={e => {
                setQ(e.target.value)
                setPage(1)
              }}
              placeholder="Buscar productos..."
              className="search-input"
            />
            <svg className="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <select
            value={category}
            onChange={e => {
              setCategory(e.target.value)
              setPage(1)
            }}
            className="category-select"
          >
            {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
          </select>
          <Link to="/cart" className="cart-button">
            🛒 Ver carrito
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="loading-message">Cargando productos...</div>
      ) : (
        <>
          <div className="products-grid">
            {products.map(p => (
              <div key={p.id} className="product-card">
                <Link to={`/product/${p.id}`}>
                  <div className="product-image-container">
                    <img src={p.images && p.images[0] ? p.images[0] : 'https://picsum.photos/800/600'} alt={p.name} className="product-image" />
                    <div className="product-badge">⭐ {p.rating.toFixed(1)}</div>
                  </div>
                </Link>
                <div className="product-content">
                  <Link to={`/product/${p.id}`}>
                    <h3 className="product-title">{p.name}</h3>
                    <p className="product-description">{p.description || 'Sin descripción'}</p>
                  </Link>
                  <div className="product-footer">
                    <div className="product-price">${p.price.toFixed(2)}</div>
                    <div className="product-stock">Stock: {p.stock}</div>
                  </div>
                  <Link to={`/product/${p.id}`} className="view-button">
                    Ver detalles
                  </Link>
                </div>
              </div>
            ))}

            {products.length === 0 && !loading && (
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

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                Anterior
              </button>
              <span>Página {page} de {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                Siguiente
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
