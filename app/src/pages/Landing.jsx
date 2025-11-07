import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { productService } from '../services/productService'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import '../styles/Landing.css'

export default function Landing() {
  const [featured, setFeatured] = useState([])
  const [featuredLoading, setFeaturedLoading] = useState(true)
  const [featuredError, setFeaturedError] = useState(null)
  
  // Estados para el carrusel
  const [currentSlide, setCurrentSlide] = useState(0)
  const [prevIndex, setPrevIndex] = useState(null)
  const [direction, setDirection] = useState('next') // 'next' or 'prev'
  
  // Datos del carrusel
  const slides = [
    {
      id: 1,
      title: "Bienvenido a La Tiendita 🛒",
      subtitle: "Descubre productos increíbles al mejor precio. Tu tienda de confianza con la mejor calidad y servicio.",
      primaryButton: "Crear cuenta gratis",
      secondaryButton: "Iniciar sesión",
      primaryLink: "/signup",
      secondaryLink: "/login",
      backgroundClass: "hero-bg-1"
    },
    {
      id: 2,
      title: "Ofertas Especiales 🔥",
      subtitle: "No te pierdas nuestras promociones exclusivas. Descuentos de hasta 50% en productos seleccionados.",
      primaryButton: "Ver ofertas",
      secondaryButton: "Explorar catálogo",
      primaryLink: "/products",
      secondaryLink: "/products",
      backgroundClass: "hero-bg-2"
    },
    {
      id: 3,
      title: "Envío Gratis 📦",
      subtitle: "Disfruta de envío gratuito en compras mayores a $500. Recibe tus productos en la comodidad de tu hogar.",
      primaryButton: "Comprar ahora",
      secondaryButton: "Más información",
      primaryLink: "/products",
      secondaryLink: "/products",
      backgroundClass: "hero-bg-3"
    },
    {
      id: 4,
      title: "Calidad Garantizada ⭐",
      subtitle: "Todos nuestros productos cuentan con garantía total. Tu satisfacción es nuestra prioridad número uno.",
      primaryButton: "Ver productos",
      secondaryButton: "Contáctanos",
      primaryLink: "/products",
      secondaryLink: "/chat",
      backgroundClass: "hero-bg-4"
    }
  ]
  
  // Auto-play del carrusel
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length)
    }, 5000) // Cambia cada 5 segundos
    
    return () => clearInterval(interval)
  }, [slides.length])
  
  // Navegación manual
  const goToSlide = (index) => {
    if (index === currentSlide) return
    setPrevIndex(currentSlide)
    setDirection(index > currentSlide ? 'next' : 'prev')
    setCurrentSlide(index)
  }
  
  const nextSlide = () => {
    setPrevIndex(currentSlide)
    setDirection('next')
    setCurrentSlide((s) => (s + 1) % slides.length)
  }
  
  const prevSlide = () => {
    setPrevIndex(currentSlide)
    setDirection('prev')
    setCurrentSlide((s) => (s - 1 + slides.length) % slides.length)
  }

  useEffect(() => {
    async function fetchFeatured() {
      try {
        setFeaturedLoading(true)
        setFeaturedError(null)
        const data = await productService.getProducts({ page: 1, per_page: 4 })
        const items = data.products || []
        setFeatured(items.slice(0, 4))
      } catch (err) {
        console.error('Error al cargar destacados:', err)
        setFeaturedError('No se pudieron cargar los productos destacados.')
      } finally {
        setFeaturedLoading(false)
      }
    }
    fetchFeatured()
  }, [])

  return (
    <div className="landing-container">
      {/* Hero Carousel Section */}
      <section className="hero-carousel">
        <div className="carousel-container">
          {slides.map((slide, index) => {
            // Determine per-slide classes to animate enter/exit directionally
            let slideClass = 'carousel-slide ' + slide.backgroundClass
            if (index === currentSlide) {
              // entering slide
              slideClass += ' active'
              slideClass += direction === 'next' ? ' enter-right' : ' enter-left'
            } else if (index === prevIndex) {
              // exiting slide
              slideClass += direction === 'next' ? ' exit-left' : ' exit-right'
            }

            return (
              <div 
                key={slide.id}
                className={slideClass}
              >
                <div className="hero-overlay"></div>
                <div className="hero-content">
                  <h1 className="hero-title">{slide.title}</h1>
                  <p className="hero-subtitle">{slide.subtitle}</p>
                  <div className="hero-buttons">
                    <Link to={slide.primaryLink} className="hero-button-primary">{slide.primaryButton}</Link>
                    <Link to={slide.secondaryLink} className="hero-button-secondary">{slide.secondaryButton}</Link>
                  </div>
                </div>
              </div>
            )
          })}
          
          {/* Botones de navegación */}
          <button 
            className="carousel-btn carousel-btn-prev" 
            onClick={prevSlide}
            aria-label="Slide anterior"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <polyline points="15,18 9,12 15,6"></polyline>
            </svg>
          </button>
          <button 
            className="carousel-btn carousel-btn-next" 
            onClick={nextSlide}
            aria-label="Siguiente slide"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <polyline points="9,18 15,12 9,6"></polyline>
            </svg>
          </button>
          
          {/* Indicadores de puntos */}
          <div className="carousel-dots">
            {slides.map((_, index) => (
              <button
                key={index}
                className={`carousel-dot ${index === currentSlide ? 'active' : ''}`}
                onClick={() => goToSlide(index)}
                aria-label={`Ir al slide ${index + 1}`}
              />
            ))}
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
        {featuredLoading && (
          <div className="featured-message">Cargando productos destacados...</div>
        )}
        {featuredError && (
          <div className="error-message">{featuredError}</div>
        )}
        {!featuredLoading && !featuredError && (
          <div className="products-grid">
            {featured.map(p => {
              const name = p.name || p.title
              const image = p.images?.[0] || getProductImageUrl(p.id) || getFallbackImageUrl()
              return (
                <Link 
                  key={p.id} 
                  to={`/product/${p.id}`} 
                  className="product-card"
                >
                  <div className="product-image-container">
                    <img 
                      src={image} 
                      alt={name} 
                      className="product-image"
                    />
                    {p.rating && (
                      <div className="product-rating">
                        ⭐ {p.rating}
                      </div>
                    )}
                  </div>
                  <div className="product-content">
                    <h3 className="product-title">
                      {name}
                    </h3>
                    <p className="product-description">{p.description}</p>
                    <div className="product-footer">
                      <span className="product-price">
                        ${p.price ? p.price.toFixed(2) : '-'}
                      </span>
                      {typeof p.stock !== 'undefined' && (
                        <span className="product-stock">Stock: {p.stock}</span>
                      )}
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
        <div className="products-cta">
          <Link to="/products" className="products-button">
            Ver todos los productos
          </Link>
        </div>
      </section>
    </div>
  )
}
