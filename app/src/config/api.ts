// Always use relative paths to avoid mixed content issues
// This works both in development and production, and with Tailscale Funnel
const getBaseUrl = () => {
  // If VITE_API_BASE_URL is explicitly set, use it
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }

  // Use relative URLs (works with same origin and proxies)
  return ''  // Relative URLs (e.g., /api/v1/products)
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
