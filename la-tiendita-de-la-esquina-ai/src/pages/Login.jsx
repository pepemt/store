import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { USERS } from '../data/mockData'
import { useAuth } from '../context/AuthContext'
import '../styles/Login.css'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    const user = USERS.find(u => u.email === email && u.password === password)
    if (!user) {
      setError('Credenciales inválidas')
      return
    }
    // usamos el login del contexto (simulado)
    login(user.email, user.password)
    navigate('/')
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h2 className="login-title">Iniciar sesión</h2>
          <p className="login-subtitle">Bienvenido de vuelta a La Tiendita</p>
        </div>

        <div className="demo-credentials">
          <div className="demo-credentials-title">Credenciales de prueba</div>
          <div className="demo-credentials-text">
            Email: demo@tiendita.com<br />
            Contraseña: password123
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit} className="login-form">
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
          
          <button type="submit" className="login-button">
            Entrar
          </button>
        </form>
        
        <div className="login-footer">
          <p className="login-footer-text">
            ¿No tienes cuenta?
          </p>
          <Link to="/signup" className="login-link">
            Regístrate aquí
          </Link>
        </div>
      </div>
    </div>
  )
}
