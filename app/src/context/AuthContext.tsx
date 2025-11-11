import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authService } from '../services/authService'

interface User {
  id?: string
  name?: string
  email?: string
  customer_id?: string
  [key: string]: unknown
}

interface SignupData {
  name: string
  email: string
  password: string
  age?: number
}

interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<User>
  logout: () => void
  signup: (data: SignupData) => Promise<User>
  updateProfile: (updates: Partial<User>) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      return JSON.parse(localStorage.getItem('tiendita_user') || 'null')
    } catch {
      return null
    }
  })

  useEffect(() => {
    if (user) {
      localStorage.setItem('tiendita_user', JSON.stringify(user))
    } else {
      localStorage.removeItem('tiendita_user')
    }
  }, [user])

  const login = async (email: string, password: string): Promise<User> => {
    try {
      const loggedUser = await authService.login(email, password)
      setUser(loggedUser as unknown as User)
      return loggedUser as unknown as User
    } catch (err) {
      console.error('Error en login:', err)
      throw err
    }
  }

  const signup = async ({ name, email, password, age }: SignupData): Promise<User> => {
    try {
      const newUser = await authService.signupNew({ name, email, password, age })
      setUser(newUser as User)
      return newUser as User
    } catch (err) {
      console.error('Error en signup:', err)
      throw err
    }
  }

  const updateProfile = (updates: Partial<User>): void => {
    setUser(prev => {
      if (!prev) return prev
      const next = { ...prev, ...updates }
      try {
        localStorage.setItem('tiendita_user', JSON.stringify(next))
      } catch {}
      return next
    })
  }

  const logout = (): void => setUser(null)

  return (
    <AuthContext.Provider value={{ user, login, logout, signup, updateProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe usarse dentro de AuthProvider')
  }
  return context
}

export default AuthContext
