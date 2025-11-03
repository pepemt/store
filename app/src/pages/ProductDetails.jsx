import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import productService from '../services/productService'
import '../styles/ProductDetails.css'

export default function ProductDetails() {
  const { id } = useParams()
  const [product, setProduct] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { add } = useCart()
  const [qty, setQty] = useState(1)
  const [added, setAdded] = useState(false)

  useEffect(() => {
    const loadProduct = async () => {
      try {
        const data = await productService.getProductById(id)
        setProduct(data)
      } catch (error) {
        console.error('Error loading product:', error)
        setProduct(null)
      } finally {
        setLoading(false)
      }
    }
    loadProduct()
  }, [id])

  const handleAdd = async () => {
    if (!product) return
    const safeQty = Math.max(1, Math.min(qty, product.stock))
    try {
      await add(product, safeQty)
      setAdded(true)
    } catch (error) {
      console.error('Error adding to cart:', error)
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-message">Cargando producto...</div>
      </div>
    )
  }

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

  return (
    <div className="product-details-container">
      <div className="product-details-grid">
          <div className="product-image-section">
          <img 
            src={product.images && product.images[0] ? product.images[0] : 'https://picsum.photos/800/600'} 
            alt={product.name} 
            className="product-main-image" 
          />
          <div className="product-image-badge">
            ⭐ {product.rating.toFixed(1)}
          </div>
        </div>

        <div className="product-info-section">
          <h1 className="product-title">{product.name}</h1>
          <div className="product-price">${product.price.toFixed(2)}</div>
          <p className="product-description">{product.description || 'Sin descripción disponible'}</p>
          
          <div className="product-meta">
            <div className="product-meta-item">
              <span className="product-meta-label">Categoría:</span>
              <span className="product-meta-value">{product.category || 'N/A'}</span>
            </div>
            <div className="product-meta-item">
              <span className="product-meta-label">Departamento:</span>
              <span className="product-meta-value">{product.department || 'N/A'}</span>
            </div>
            <div className="product-meta-item">
              <span className="product-meta-label">Grupo de producto:</span>
              <span className="product-meta-value">{product.product_group || 'N/A'}</span>
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
            
            <button onClick={handleAdd} className="add-to-cart-button" disabled={added}>
              {added ? '✓ Agregado' : '🛒 Agregar al carrito'}
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
