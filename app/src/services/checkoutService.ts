import { config } from '../config/api'

export interface CreateSessionResponse {
  session_id: string
  checkout_url: string
  order_id: number
}

export interface SessionStatusResponse {
  status: string
  payment_status: string
  order_id?: number
}

export interface StripeConfig {
  publishable_key: string | null
}

export const checkoutService = {
  /**
   * Crea una sesión de Stripe Checkout
   */
  async createSession(customerId: string): Promise<CreateSessionResponse> {
    const response = await fetch(`${config.CHECKOUT_URL}/create-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ customer_id: customerId }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Error al crear sesión de pago')
    }

    return response.json()
  },

  /**
   * Obtiene el estado de una sesión de checkout
   */
  async getSessionStatus(sessionId: string): Promise<SessionStatusResponse> {
    const response = await fetch(`${config.CHECKOUT_URL}/session/${sessionId}`)

    if (!response.ok) {
      throw new Error('Error al verificar estado del pago')
    }

    return response.json()
  },

  /**
   * Obtiene la configuración pública de Stripe
   */
  async getConfig(): Promise<StripeConfig> {
    const response = await fetch(`${config.CHECKOUT_URL}/config`)

    if (!response.ok) {
      throw new Error('Error al obtener configuración de Stripe')
    }

    return response.json()
  },

  /**
   * Redirige al usuario a Stripe Checkout
   */
  redirectToCheckout(checkoutUrl: string): void {
    window.location.href = checkoutUrl
  },
}

export default checkoutService
