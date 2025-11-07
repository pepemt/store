import React from 'react'
import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import '../styles/Cart.css'

export default function Cart() {
  const {
    items,
    remove,
    updateQty,
    clear,
    total,
    loading,
    error,
    mutating,
  } = useCart()

  const handleChangeQty = (id, value) => {
    const q = Math.max(1, Number(value) || 1)
    updateQty(id, q).catch(() => {})
  }

  if (loading) {
    return (
      <div className="cart-container">
        <div className="loading-state">Cargando carrito...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="cart-container">
        <div className="error-state">
          <div className="error-message">{error}</div>
          <Link to="/products" className="empty-cart-link">
            Volver a productos
          </Link>
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="cart-container">
        <div className="empty-cart">
          <div className="empty-cart-icon">🛒</div>
          <h2 className="empty-cart-title">Tu carrito está vacío</h2>
          <p className="empty-cart-text">
            Agrega algunos productos increíbles a tu carrito para comenzar tu compra.
          </p>
          <Link to="/products" className="empty-cart-link">
            Ver productos
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="cart-container">
      <div className="cart-header">
        <h1 className="cart-title">Tu carrito</h1>
        <div className="cart-items-count">
          {items.length} {items.length === 1 ? 'producto' : 'productos'}
        </div>
      </div>

      <div className="cart-items">
        {items.map(item => {
          const priceText =
            typeof item.price === 'number' ? item.price.toFixed(2) : '—'
          const lineTotal =
            typeof item.price === 'number'
              ? (item.price * (item.qty || 0)).toFixed(2)
              : '—'
          const image = item.images?.[0] || ''
          return (
            <div key={item.id} className="cart-item">
              <img src={image} alt={item.name} className="cart-item-image" />
              <div className="cart-item-info">
                <Link to={`/product/${item.id}`} className="cart-item-title">
                  {item.name}
                </Link>
                <div className="cart-item-price">${priceText} c/u</div>
              </div>
              <div className="cart-item-controls">
                <div className="quantity-controls">
                  <input
                    type="number"
                    value={item.qty}
                    min="1"
                    onChange={e => handleChangeQty(item.id, e.target.value)}
                    className="quantity-input"
                    disabled={mutating}
                  />
                </div>
                <div className="cart-item-total">${lineTotal}</div>
                <button
                  onClick={() => remove(item.id).catch(() => {})}
                  className="remove-button"
                  disabled={mutating}
                >
                  Eliminar
                </button>
              </div>
            </div>
          )
        })}
      </div>

      <div className="cart-summary">
        <div className="cart-summary-header">
          <h2 className="cart-summary-title">Resumen del pedido</h2>
        </div>

        <div className="cart-total">
          <span className="cart-total-label">Total:</span>
          <span className="cart-total-amount">${total.toFixed(2)}</span>
        </div>

        <div className="cart-actions">
          <button
            onClick={() => clear().catch(() => {})}
            className="clear-cart-button"
            disabled={mutating}
          >
            Vaciar carrito
          </button>
          <Link to="/checkout" className="checkout-button">
            Ir a pagar
          </Link>
        </div>
      </div>
    </div>
  )
}
