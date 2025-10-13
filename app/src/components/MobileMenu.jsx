import React, { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from './ThemeToggle'
import '../styles/MobileMenu.css'

export default function MobileMenu({ open, onClose }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const go = (to) => {
    onClose()
    navigate(to)
  }

  return (
    <div className={"mm-overlay" + (open ? ' mm-open' : ' mm-closed')} onClick={() => open && onClose()}>
      <aside className={"mm-drawer" + (open ? ' mm-open' : ' mm-closed')} onClick={(e) => e.stopPropagation()}>
        <div className="mm-header">
          <h3>Menú</h3>
          <button className="mm-close" onClick={onClose}>×</button>
        </div>

        <div className="mm-user">
          {user ? (
            <>
              <div className="mm-avatar">{user.name?.slice(0,1).toUpperCase()}</div>
              <div>
                <div className="mm-name">{user.name}</div>
                <div className="mm-email">{user.email}</div>
              </div>
            </>
          ) : (
            <div className="mm-guest">Invitado</div>
          )}
        </div>

        <div className="mm-theme">
          <label className="mm-theme-label">Tema</label>
          <ThemeToggle />
        </div>

        <nav className="mm-nav">
          <button className="mm-link" onClick={() => go('/profile')}>Perfil</button>
          <button className="mm-link" onClick={() => go('/settings')}>Configuración</button>
          <button className="mm-link" onClick={() => go('/products')}>Productos</button>
        </nav>

        <div className="mm-footer">
          {user ? (
            <>
              <button className="mm-logout" onClick={() => { logout(); onClose(); navigate('/') }}>Salir</button>
            </>
          ) : (
            <div className="mm-auth">
              <button className="mm-btn mm-login" onClick={() => go('/login')}>Entrar</button>
              <button className="mm-btn mm-signup" onClick={() => go('/signup')}>Registrarse</button>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
