import React from 'react'
import { Link } from 'react-router-dom'
import { PRODUCTS } from '../data/mockData'
import '../styles/Landing.css'

export default function Landing() {
  // mostramos algunos productos destacados (primeros 4)
  const featured = PRODUCTS.slice(0, 4)

  return (
    <div className="landing-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-overlay"></div>
        <div className="hero-content">
          <h1 className="hero-title">
            Bienvenido a La Tiendita 🛒
          </h1>
          <p className="hero-subtitle">
            Descubre productos increíbles al mejor precio. Tu tienda de confianza con la mejor calidad y servicio.
          </p>
          <div className="hero-buttons">
            <Link to="/signup" className="hero-button-primary">
              Crear cuenta gratis
            </Link>
            <Link to="/login" className="hero-button-secondary">
              Iniciar sesión
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="feature-card">
          <div className="feature-icon blue">🚚</div>
          <h3 className="feature-title">Envío Rápido</h3>
          <p className="feature-description">Recibe tus productos en 24-48 horas</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon green">💎</div>
          <h3 className="feature-title">Calidad Premium</h3>
          <p className="feature-description">Solo productos de la mejor calidad</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon purple">🛡️</div>
          <h3 className="feature-title">Garantía Total</h3>
          <p className="feature-description">30 días de garantía en todos los productos</p>
        </div>
      </section>

      {/* Featured Products */}
      <section className="products-section">
        <div className="products-header">
          <h2 className="products-title">
            Productos Destacados
          </h2>
          <p className="products-subtitle">Los favoritos de nuestros clientes</p>
        </div>
        <div className="products-grid">
          {featured.map(p => (
            <Link 
              key={p.id} 
              to={`/product/${p.id}`} 
              className="product-card"
            >
              <div className="product-image-container">
                <img 
                  src={p.images[0]} 
                  alt={p.title} 
                  className="product-image"
                />
                <div className="product-rating">
                  ⭐ {p.rating}
                </div>
              </div>
              <div className="product-content">
                <h3 className="product-title">
                  {p.title}
                </h3>
                <p className="product-description">{p.description}</p>
                <div className="product-footer">
                  <span className="product-price">${p.price}</span>
                  <span className="product-stock">Stock: {p.stock}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
        <div className="products-cta">
          <Link to="/products" className="products-button">
            Ver todos los productos
          </Link>
        </div>
      </section>
    </div>
  )
}
