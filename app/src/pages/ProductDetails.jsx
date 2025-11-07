import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { productService } from '../services/productService'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import '../styles/ProductDetails.css'

export default function ProductDetails() {
  const { id } = useParams()
  const { add } = useCart()

  const [product, setProduct] = useState(null)
  const [qty, setQty] = useState(1)
  const [added, setAdded] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchProduct() {
      try {
        setLoading(true)
        const data = await productService.getProductById(id)
        setProduct(data)
      } catch (err) {
        console.error('Error al obtener producto:', err)
        setError('No se pudo cargar la informacion del producto.')
      } finally {
        setLoading(false)
      }
    }
    fetchProduct()
  }, [id])

  const handleAdd = () => {
    if (!product) return
    const safeQty = Math.max(1, Math.min(qty, product.stock || 1))
    const normalizedProduct = {
      ...product,
      title: product.name || product.title,
      images: product.images && product.images.length > 0
        ? product.images
        : [getProductImageUrl(product.id)],
    }
    add(normalizedProduct, safeQty)
    setAdded(true)
  }

  if (loading) {
    return <div className="loading-message">Cargando producto...</div>
  }

  if (error) {
    return (
      <div className="not-found">
        <div className="not-found-icon">⚠️</div>
        <h2 className="not-found-title">Error</h2>
        <p className="not-found-text">{error}</p>
        <Link to="/products" className="not-found-link">
          Volver al catalogo
        </Link>
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
          Ver catalogo de productos
        </Link>
      </div>
    )
  }

  const displayName = product.name || product.title || 'Producto'
  const heroImage = product.images?.[0] || getProductImageUrl(product.id) || getFallbackImageUrl()

  return (
    <div className="product-details-container">
      <div className="product-details-grid">
        <div className="product-image-section">
          <img 
            src={heroImage} 
            alt={displayName}
            className="product-main-image"
          />
          {product.rating && (
            <div className="product-image-badge">
              ⭐ {product.rating}
            </div>
          )}
        </div>

        <div className="product-info-section">
          <h1 className="product-title">{displayName}</h1>
          <div className="product-price">
            ${product.price ? product.price.toFixed(2) : '-'}
          </div>
          <p className="product-description">{product.description}</p>
          
          <div className="product-meta">
            {product.category && (
              <div className="product-meta-item">
                <span className="product-meta-label">Categoria:</span>
                <span className="product-meta-value">{product.category}</span>
              </div>
            )}
            {product.department && (
              <div className="product-meta-item">
                <span className="product-meta-label">Departamento:</span>
                <span className="product-meta-value">{product.department}</span>
              </div>
            )}
            {product.stock !== undefined && (
              <div className="product-meta-item">
                <span className="product-meta-label">Stock disponible:</span>
                <span className="product-meta-value">{product.stock} unidades</span>
              </div>
            )}
          </div>

          <div className="product-actions">
            <div className="quantity-section">
              <label className="quantity-label">Cantidad:</label>
              <input
                type="number"
                value={qty}
                min="1"
                max={product.stock || 99}
                onChange={e => setQty(Number(e.target.value))}
                className="quantity-input"
              />
            </div>
            
            <button onClick={handleAdd} className="add-to-cart-button">
              🛒 Agregar al carrito
            </button>
            
            <Link to="/products" className="continue-shopping-button">
              Seguir comprando
            </Link>

            {added && (
              <div className="success-message">
                ¡Agregado al carrito! <Link to="/cart">Ir al carrito</Link>
              </div>
            )}
          </div>

          {product.rating && (
            <div className="product-rating">
              <h3 className="rating-title">Calificacion</h3>
              <div className="rating-value">
                <span className="rating-stars">★★★★★</span>
                <span>{product.rating} / 5</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
