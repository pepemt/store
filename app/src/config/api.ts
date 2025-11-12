// In production (built), use relative paths since frontend is served from same server
// In development, use explicit localhost URL for CORS
const getBaseUrl = () => {
  // If VITE_API_BASE_URL is explicitly set, use it
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }

  // In production build, use relative path (same origin)
  if (import.meta.env.PROD) {
    return ''  // Relative URLs (e.g., /api/v1/products)
  }

  // In development, use localhost
  return 'http://localhost:8000'
}

const API_BASE_URL = getBaseUrl()

export const config = {
  BASE_URL: API_BASE_URL,
  AUTH_URL: `${API_BASE_URL}/api/v1/auth`,
  PRODUCTS_URL: `${API_BASE_URL}/api/v1/products`,
  CART_URL: `${API_BASE_URL}/api/v1/cart`,
  IMAGES_URL: `${API_BASE_URL}/api/v1/images`,
}

export const getProductImageUrl = (productId: string | null | undefined): string | null => {
  if (!productId) return null
  return `${config.IMAGES_URL}/${productId}`
}

export const getFallbackImageUrl = (): string => {
  return `${config.IMAGES_URL}/komo`
}

export default config
