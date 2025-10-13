import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { useAuth } from '../context/AuthContext'
import '../styles/Checkout.css'

export default function Checkout() {
  const { items, total, clear } = useCart()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [isProcessing, setIsProcessing] = useState(false)
  const [orderComplete, setOrderComplete] = useState(false)

  // Estado del formulario
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: '',
    address: '',
    city: '',
    zipCode: '',
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    cardName: ''
  })

  const [errors, setErrors] = useState({})

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    // Limpiar error al escribir
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.name.trim()) newErrors.name = 'Nombre es requerido'
    if (!formData.email.trim()) newErrors.email = 'Email es requerido'
    if (!formData.phone.trim()) newErrors.phone = 'Teléfono es requerido'
    if (!formData.address.trim()) newErrors.address = 'Dirección es requerida'
    if (!formData.city.trim()) newErrors.city = 'Ciudad es requerida'
    if (!formData.zipCode.trim()) newErrors.zipCode = 'Código postal es requerido'
    if (!formData.cardNumber.trim()) newErrors.cardNumber = 'Número de tarjeta es requerido'
    if (!formData.expiryDate.trim()) newErrors.expiryDate = 'Fecha de vencimiento es requerida'
    if (!formData.cvv.trim()) newErrors.cvv = 'CVV es requerido'
    if (!formData.cardName.trim()) newErrors.cardName = 'Nombre en la tarjeta es requerido'

    // Validaciones específicas
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (formData.email && !emailRegex.test(formData.email)) {
      newErrors.email = 'Email inválido'
    }

    if (formData.cardNumber && formData.cardNumber.replace(/\s/g, '').length < 16) {
      newErrors.cardNumber = 'Número de tarjeta inválido'
    }

    if (formData.cvv && (formData.cvv.length < 3 || formData.cvv.length > 4)) {
      newErrors.cvv = 'CVV inválido'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!validateForm()) return

    setIsProcessing(true)

    try {
      // Simular procesamiento de pago
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Vaciar carrito y mostrar éxito
      clear()
      setOrderComplete(true)
      
      // Redirigir después de 3 segundos
      setTimeout(() => {
        navigate('/')
      }, 3000)
      
    } catch (error) {
      console.error('Error procesando pago:', error)
      setErrors({ general: 'Error procesando el pago. Intenta nuevamente.' })
    } finally {
      setIsProcessing(false)
    }
  }

  // Si el carrito está vacío
  if (items.length === 0 && !orderComplete) {
    return (
      <div className="checkout-container">
        <div className="empty-checkout">
          <div className="empty-checkout-icon">🛒</div>
          <h2 className="empty-checkout-title">No hay productos en tu carrito</h2>
          <p className="empty-checkout-text">
            Agrega algunos productos antes de proceder al pago.
          </p>
          <Link to="/products" className="empty-checkout-link">
            Ver productos
          </Link>
        </div>
      </div>
    )
  }

  // Si la orden se completó
  if (orderComplete) {
    return (
      <div className="checkout-container">
        <div className="order-success">
          <div className="success-icon">✅</div>
          <h2 className="success-title">¡Pago exitoso!</h2>
          <p className="success-text">
            Tu orden ha sido procesada correctamente. Recibirás un email de confirmación pronto.
          </p>
          <div className="success-amount">
            Total pagado: <strong>${total.toFixed(2)}</strong>
          </div>
          <p className="redirect-text">
            Serás redirigido al inicio en unos segundos...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="checkout-container">
      <div className="checkout-header">
        <h1 className="checkout-title">Finalizar compra</h1>
        <Link to="/cart" className="back-to-cart">
          ← Volver al carrito
        </Link>
      </div>

      <div className="checkout-content">
        <div className="checkout-form-section">
          <form onSubmit={handleSubmit} className="checkout-form">
            {errors.general && (
              <div className="error-message general-error">
                {errors.general}
              </div>
            )}

            {/* Datos del cliente */}
            <div className="form-section">
              <h3 className="section-title">Datos del cliente</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Nombre completo</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    className={`form-input ${errors.name ? 'error' : ''}`}
                    placeholder="Tu nombre completo"
                  />
                  {errors.name && <span className="field-error">{errors.name}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    className={`form-input ${errors.email ? 'error' : ''}`}
                    placeholder="tu@email.com"
                  />
                  {errors.email && <span className="field-error">{errors.email}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Teléfono</label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                    className={`form-input ${errors.phone ? 'error' : ''}`}
                    placeholder="+1 (555) 123-4567"
                  />
                  {errors.phone && <span className="field-error">{errors.phone}</span>}
                </div>
              </div>
            </div>

            {/* Dirección de envío */}
            <div className="form-section">
              <h3 className="section-title">Dirección de envío</h3>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label className="form-label">Dirección</label>
                  <input
                    type="text"
                    name="address"
                    value={formData.address}
                    onChange={handleInputChange}
                    className={`form-input ${errors.address ? 'error' : ''}`}
                    placeholder="Calle y número"
                  />
                  {errors.address && <span className="field-error">{errors.address}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Ciudad</label>
                  <input
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleInputChange}
                    className={`form-input ${errors.city ? 'error' : ''}`}
                    placeholder="Tu ciudad"
                  />
                  {errors.city && <span className="field-error">{errors.city}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Código postal</label>
                  <input
                    type="text"
                    name="zipCode"
                    value={formData.zipCode}
                    onChange={handleInputChange}
                    className={`form-input ${errors.zipCode ? 'error' : ''}`}
                    placeholder="12345"
                  />
                  {errors.zipCode && <span className="field-error">{errors.zipCode}</span>}
                </div>
              </div>
            </div>

            {/* Datos de pago */}
            <div className="form-section">
              <h3 className="section-title">Método de pago</h3>
              <div className="payment-info">
                <div className="payment-icon">💳</div>
                <p>Pago seguro con tarjeta de crédito o débito</p>
              </div>
              
              <div className="form-grid">
                <div className="form-group full-width">
                  <label className="form-label">Número de tarjeta</label>
                  <input
                    type="text"
                    name="cardNumber"
                    value={formData.cardNumber}
                    onChange={handleInputChange}
                    className={`form-input ${errors.cardNumber ? 'error' : ''}`}
                    placeholder="1234 5678 9012 3456"
                    maxLength="19"
                  />
                  {errors.cardNumber && <span className="field-error">{errors.cardNumber}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Fecha de vencimiento</label>
                  <input
                    type="text"
                    name="expiryDate"
                    value={formData.expiryDate}
                    onChange={handleInputChange}
                    className={`form-input ${errors.expiryDate ? 'error' : ''}`}
                    placeholder="MM/AA"
                    maxLength="5"
                  />
                  {errors.expiryDate && <span className="field-error">{errors.expiryDate}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">CVV</label>
                  <input
                    type="text"
                    name="cvv"
                    value={formData.cvv}
                    onChange={handleInputChange}
                    className={`form-input ${errors.cvv ? 'error' : ''}`}
                    placeholder="123"
                    maxLength="4"
                  />
                  {errors.cvv && <span className="field-error">{errors.cvv}</span>}
                </div>

                <div className="form-group full-width">
                  <label className="form-label">Nombre en la tarjeta</label>
                  <input
                    type="text"
                    name="cardName"
                    value={formData.cardName}
                    onChange={handleInputChange}
                    className={`form-input ${errors.cardName ? 'error' : ''}`}
                    placeholder="Como aparece en tu tarjeta"
                  />
                  {errors.cardName && <span className="field-error">{errors.cardName}</span>}
                </div>
              </div>
            </div>

            <button 
              type="submit" 
              className={`checkout-submit-button ${isProcessing ? 'processing' : ''}`}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <span className="spinner"></span>
                  Procesando pago...
                </>
              ) : (
                <>
                  💳 Pagar ${total.toFixed(2)}
                </>
              )}
            </button>
          </form>
        </div>

        {/* Resumen del pedido */}
        <div className="order-summary">
          <h3 className="summary-title">Resumen del pedido</h3>
          
          <div className="summary-items">
            {items.map(item => (
              <div key={item.id} className="summary-item">
                <img 
                  src={item.images?.[0]} 
                  alt={item.title} 
                  className="summary-item-image" 
                />
                <div className="summary-item-info">
                  <h4 className="summary-item-title">{item.title}</h4>
                  <div className="summary-item-details">
                    <span className="summary-item-qty">Cantidad: {item.qty}</span>
                    <span className="summary-item-price">${(item.price * item.qty).toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="summary-totals">
            <div className="summary-row">
              <span>Subtotal:</span>
              <span>${total.toFixed(2)}</span>
            </div>
            <div className="summary-row">
              <span>Envío:</span>
              <span>Gratis</span>
            </div>
            <div className="summary-row total">
              <span>Total:</span>
              <span>${total.toFixed(2)}</span>
            </div>
          </div>

          <div className="security-info">
            <div className="security-icon">🔒</div>
            <p>Pago 100% seguro y encriptado</p>
          </div>
        </div>
      </div>
    </div>
  )
}