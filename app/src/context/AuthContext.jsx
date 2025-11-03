import React, { createContext, useContext, useState, useEffect } from 'react'
import authService from '../services/authService'

// Context para autenticación
const AuthContext = createContext()

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tiendita_user') || 'null') } catch { return null }
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) {
      localStorage.setItem('tiendita_user', JSON.stringify(user))
    } else {
      localStorage.removeItem('tiendita_user')
    }
  }, [user])

  // login: autentica con el backend API
  const login = async (email, password) => {
    setLoading(true)
    try {
      const response = await authService.login(email, password)
      const userData = {
        id: response.customer_id,
        name: response.name,
        email: response.email,
      }
      setUser(userData)
      return userData
    } catch (error) {
      throw error
    } finally {
      setLoading(false)
    }
  }

  // signup: crea nuevo usuario con el backend API
  const signup = async ({ name, email, password, age, postal_code }) => {
    setLoading(true)
    try {
      const response = await authService.signupNew({ name, email, password, age, postal_code })
      const userData = {
        id: response.customer_id,
        name: name,
        email: email,
      }
      setUser(userData)
      return userData
    } catch (error) {
      throw error
    } finally {
      setLoading(false)
    }
  }

  // signupLink: vincula un usuario existente con credenciales
  const signupLink = async ({ customer_id, name, email, password }) => {
    setLoading(true)
    try {
      const response = await authService.signupLink({ customer_id, name, email, password })
      const userData = {
        id: response.customer_id,
        name: name,
        email: email,
      }
      setUser(userData)
      return userData
    } catch (error) {
      throw error
    } finally {
      setLoading(false)
    }
  }

  // updateProfile: actualiza datos del usuario en el contexto y localStorage
  const updateProfile = async (updates) => {
    setUser(prev => {
      if (!prev) return prev
      const next = { ...prev, ...updates }
      try { localStorage.setItem('tiendita_user', JSON.stringify(next)) } catch {}
      return next
    })
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('tiendita_user')
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, signup, signupLink, updateProfile, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
export default AuthContext
