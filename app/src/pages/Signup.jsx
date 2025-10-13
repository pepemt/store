import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { USERS } from '../data/mockData'
import { useAuth } from '../context/AuthContext'
import '../styles/Signup.css'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (USERS.some(u => u.email === email)) {
      setError('Este correo ya está registrado')
      return
    }
    const newUser = {
      id: 'u' + (USERS.length + 1),
      name,
      email,
      password,
      createdAt: new Date().toISOString()
    }
    USERS.push(newUser) // mutamos mock
    signup(newUser)     // simulamos login automático
    navigate('/')
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
          
          <button type="submit" className="signup-button">
            Registrarse
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
