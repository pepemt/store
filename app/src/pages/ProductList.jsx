import React, { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { PRODUCTS, CATEGORIES } from '../data/mockData'
import '../styles/ProductList.css'

export default function ProductList() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('Todos')

  // filtro simple en memoria (mock)
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase()
    return PRODUCTS.filter(p => {
      const matchesCat = category === 'Todos' ? true : p.category === category
      if (!term) return matchesCat
      const inTitle = p.title.toLowerCase().includes(term)
      const inDesc = p.description.toLowerCase().includes(term)
      return matchesCat && (inTitle || inDesc)
    })
  }, [q, category])

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
            {CATEGORIES.map(cat => <option key={cat}>{cat}</option>)}
          </select>
          <Link to="/cart" className="cart-button">
            🛒 Ver carrito
          </Link>
        </div>
      </div>

      <div className="products-grid">
        {filtered.map(p => (
          <div key={p.id} className="product-card">
            <Link to={`/product/${p.id}`}>
              <div className="product-image-container">
                <img src={p.images[0]} alt={p.title} className="product-image" />
                <div className="product-badge">⭐ {p.rating}</div>
              </div>
            </Link>
            <div className="product-content">
              <Link to={`/product/${p.id}`}>
                <h3 className="product-title">{p.title}</h3>
                <p className="product-description">{p.description}</p>
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

        {filtered.length === 0 && (
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
