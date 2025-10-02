import React, { createContext, useContext, useState, useEffect } from 'react'
import { USERS } from '../data/mockData'

// Context para autenticación (mock)
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

  // login: busca en USERS (mock) y establece el user si coincide
  const login = (email, password) => {
    const found = USERS.find(u => u.email === email && u.password === password)
    if (!found) {
      throw new Error('Credenciales inválidas')
    }
    setUser({ id: found.id, name: found.name, email: found.email, createdAt: found.createdAt })
    return found
  }

  // signup: agrega a USERS (mock) y loguea
  const signup = ({ name, email, password }) => {
    if (USERS.some(u => u.email === email)) {
      throw new Error('Correo ya registrado')
    }
    const newUser = {
      id: 'u' + (USERS.length + 1),
      name,
      email,
      password,
      createdAt: new Date().toISOString()
    }
    USERS.push(newUser)
    setUser({ id: newUser.id, name: newUser.name, email: newUser.email, createdAt: newUser.createdAt })
    return newUser
  }

  const logout = () => setUser(null)

  return (
    <AuthContext.Provider value={{ user, login, logout, signup }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
export default AuthContext
