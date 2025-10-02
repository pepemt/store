import React, { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { PRODUCTS } from '../data/mockData'
import { useCart } from '../context/CartContext'
import '../styles/ProductDetails.css'

export default function ProductDetails() {
  const { id } = useParams()
  const product = PRODUCTS.find(p => p.id === id)
  const navigate = useNavigate()
  const { add } = useCart()
  const [qty, setQty] = useState(1)
  const [added, setAdded] = useState(false)

  if (!product) {
    return (
      <div className="not-found">
        <div className="not-found-icon">🔍</div>
        <h2 className="not-found-title">Producto no encontrado</h2>
        <p className="not-found-text">
          El producto que buscas no existe o ha sido eliminado.
        </p>
        <Link to="/products" className="not-found-link">
          Ver catálogo de productos
        </Link>
      </div>
    )
  }

  const handleAdd = () => {
    const safeQty = Math.max(1, Math.min(qty, product.stock))
    add({ ...product }, safeQty)
    setAdded(true)
    // opcional: redirigir al carrito
    // navigate('/cart')
  }

  return (
    <div className="product-details-container">
      <div className="product-details-grid">
        <div className="product-image-section">
          <img 
            src={product.images[0]} 
            alt={product.title} 
            className="product-main-image" 
          />
          <div className="product-image-badge">
            ⭐ {product.rating}
          </div>
        </div>

        <div className="product-info-section">
          <h1 className="product-title">{product.title}</h1>
          <div className="product-price">${product.price.toFixed(2)}</div>
          <p className="product-description">{product.description}</p>
          
          <div className="product-meta">
            <div className="product-meta-item">
              <span className="product-meta-label">Categoría:</span>
              <span className="product-meta-value">{product.category}</span>
            </div>
            <div className="product-meta-item">
              <span className="product-meta-label">Stock disponible:</span>
              <span className="product-meta-value">{product.stock} unidades</span>
            </div>
          </div>

          <div className="product-actions">
            <div className="quantity-section">
              <label className="quantity-label">Cantidad:</label>
              <input
                type="number"
                value={qty}
                min="1"
                max={product.stock}
                onChange={e => setQty(Number(e.target.value))}
                className="quantity-input"
              />
            </div>
            
            <button onClick={handleAdd} className="add-to-cart-button">
              🛒 Agregar al carrito
            </button>
            
            <Link to="/products" className="continue-shopping-button">
              ← Seguir comprando
            </Link>

            {added && (
              <div className="success-message">
                ¡Agregado al carrito! <Link to="/cart">Ir al carrito</Link>
              </div>
            )}
          </div>

          <div className="product-rating">
            <h3 className="rating-title">Calificación</h3>
            <div className="rating-value">
              <span className="rating-stars">⭐⭐⭐⭐⭐</span>
              <span>{product.rating} / 5</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
