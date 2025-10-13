import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import '../styles/Header.css'
import MobileMenu from './MobileMenu'
import { useState } from 'react'

// Header simple con logo, búsqueda (navega a /products?q=...), enlaces y contador de carrito.
export default function Header() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const { count } = useCart()
  const navigate = useNavigate()

  const handleSearch = (e) => {
    e.preventDefault()
    const q = new FormData(e.target).get('q') || ''
    const qs = q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ''
    navigate(`/products${qs}`)
  }

  return (
    <header className="header">
      <div className="header-container">
        <div className="header-left">
          <button className="hamburger" onClick={() => setMenuOpen(true)} aria-label="Abrir menú">☰</button>
          <Link to="/" className="logo">
            🛒 La Tiendita
          </Link>
        </div>

        <form onSubmit={handleSearch} className="search-form">
          <div className="search-container">
            <input 
              name="q" 
              placeholder="Buscar productos..." 
              className="search-input" 
            />
            <svg className="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button type="submit" className="search-button">
            Buscar
          </button>
        </form>

  <nav className="nav">
          <Link to="/products" className="nav-link">Productos</Link>

          {user ? (
            <div className="user-section">
              <span className="user-greeting">
                Hola, <strong className="user-name">{user.name}</strong>
              </span>
              <button
                onClick={() => { logout(); navigate('/') }}
                className="logout-button"
              >
                Salir
              </button>
            </div>
          ) : (
            <div className="auth-buttons">
              <Link to="/login" className="login-button">Entrar</Link>
              <Link to="/signup" className="signup-button">Registrarse</Link>
            </div>
          )}

          <Link to="/cart" className="cart-button">
            <svg className="cart-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2 7m12-7l2 7m-6-7v7" />
            </svg>
            <span className="cart-text">Carrito</span>
            {count > 0 && (
              <span className="cart-badge">{count}</span>
            )}
          </Link>
        </nav>
        <MobileMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
      </div>
    </header>
  )
}
