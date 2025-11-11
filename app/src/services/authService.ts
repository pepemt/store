import { config } from '../config/api'

interface LoginResponse {
  user: {
    id: string
    name: string
    email: string
    customer_id?: string
  }
  token?: string
}

interface SignupNewData {
  name: string
  email: string
  password: string
  age?: number
  postal_code?: string
}

interface SignupLinkData {
  customer_id: string
  name: string
  email: string
  password: string
}

interface UserInfo {
  id: string
  name: string
  email: string
  customer_id?: string
  age?: number
  postal_code?: string
}

interface UnlinkedCustomer {
  customer_id: string
  [key: string]: unknown
}

export const authService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const response = await fetch(`${config.AUTH_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Error al iniciar sesión')
      }

      return data
    } catch (error) {
      console.error('Error en login:', error)
      throw error
    }
  },

  async signupNew(userData: SignupNewData): Promise<UserInfo> {
    try {
      const { name, email, password, age, postal_code = '00000' } = userData

      const response = await fetch(`${config.AUTH_URL}/signup/new`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, password, age, postal_code }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Error al crear cuenta')
      }

      return data
    } catch (error) {
      console.error('Error en signup:', error)
      throw error
    }
  },

  async signupLink(userData: SignupLinkData): Promise<UserInfo> {
    try {
      const { customer_id, name, email, password } = userData

      const response = await fetch(`${config.AUTH_URL}/signup/link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ customer_id, name, email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Error al vincular cuenta')
      }

      return data
    } catch (error) {
      console.error('Error en signup vinculado:', error)
      throw error
    }
  },

  async getUser(customerId: string): Promise<UserInfo> {
    try {
      const response = await fetch(`${config.AUTH_URL}/user/${customerId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Error al obtener información del usuario')
      }

      return data
    } catch (error) {
      console.error('Error al obtener usuario:', error)
      throw error
    }
  },

  async getUnlinkedCustomers(limit = 10, offset = 0): Promise<UnlinkedCustomer[]> {
    try {
      const response = await fetch(
        `${config.AUTH_URL}/customers/unlinked?limit=${limit}&offset=${offset}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Error al obtener clientes no vinculados')
      }

      return data
    } catch (error) {
      console.error('Error al obtener clientes no vinculados:', error)
      throw error
    }
  },
}

export default authService
