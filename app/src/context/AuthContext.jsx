import React, { createContext, useContext, useState, useEffect } from 'react'
import { USERS } from '../data/mockData'
import { authService } from '../services/authService'

// Context para autenticación (backend)
// Guarda el usuario en localStorage (solo para desarrollo)
const AuthContext = createContext()

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tiendita_user') || 'null') } catch { return null }
  })
  
  useEffect(() => {
    if (user) {
      localStorage.setItem('tiendita_user', JSON.stringify(user))
    } else {
      localStorage.removeItem('tiendita_user')
    }
  }, [user])

  // login: busca en USERS en backend y establece el user si coincide
  const login = async (email, password) => {
    try {
      const loggedUser = await authService.login(email, password)
      setUser(loggedUser)
      return loggedUser
    } catch (err) {
      console.error('Error en login:', err)
      throw err
    }
  }

  // signup: agrega a USERS (backend) y loguea
  const signup = async ({ name, email, password, age }) => {
    try {
      const newUser = await authService.signupNew({ name, email, password, age })
      setUser(newUser)
      return newUser
    } catch (err) {
      console.error('Error en signup:', err)
      throw err
    }
  }

  // updateProfile: actualiza datos del usuario en el contexto y localStorage
  const updateProfile = (updates) => {
    setUser(prev => {
      if (!prev) return prev
      const next = { ...prev, ...updates }
      try { localStorage.setItem('tiendita_user', JSON.stringify(next)) } catch {}
      return next
    })
  }

  const logout = () => setUser(null)

  return (
    <AuthContext.Provider value={{ user, login, logout, signup, updateProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
export default AuthContext
