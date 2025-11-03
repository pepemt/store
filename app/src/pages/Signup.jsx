import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import '../styles/Signup.css'

export default function Signup() {
  const { signup, loading } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    
    try {
      await signup({ name, email, password })
      navigate('/')
    } catch (err) {
      setError(err.message || 'Error al crear cuenta')
    }
  }

  return (
    <div className="signup-container">
      <div className="signup-card">
        <div className="signup-header">
          <h2 className="signup-title">Crear cuenta</h2>
          <p className="signup-subtitle">Únete a La Tiendita y descubre productos increíbles</p>
        </div>

        <div className="password-requirements">
          <div className="password-requirements-title">Requisitos de contraseña</div>
          <ul className="password-requirements-list">
            <li>Mínimo 6 caracteres</li>
            <li>Puede contener letras y números</li>
          </ul>
        </div>

        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit} className="signup-form">
          <div className="form-group">
            <input
              type="text"
              placeholder=" "
              value={name}
              onChange={e => setName(e.target.value)}
              className="form-input"
              required
            />
            <label className="form-label">Nombre completo</label>
          </div>
          
          <div className="form-group">
            <input
              type="email"
              placeholder=" "
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="form-input"
              required
            />
            <label className="form-label">Correo electrónico</label>
          </div>
          
          <div className="form-group">
            <input
              type="password"
              placeholder=" "
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="form-input"
              required
            />
            <label className="form-label">Contraseña</label>
          </div>
          
          <button type="submit" className="signup-button" disabled={loading}>
            {loading ? 'Creando cuenta...' : 'Registrarse'}
          </button>
        </form>
        
        <div className="signup-footer">
          <p className="signup-footer-text">
            ¿Ya tienes cuenta?
          </p>
          <Link to="/login" className="signup-link">
            Inicia sesión aquí
          </Link>
        </div>
      </div>
    </div>
  )
}
