// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const config = {
  BASE_URL: API_BASE_URL,
  AUTH_URL: `${API_BASE_URL}/api/v1/auth`,
  PRODUCTS_URL: `${API_BASE_URL}/api/v1/products`,
  CART_URL: `${API_BASE_URL}/api/v1/cart`,
  IMAGES_URL: `${API_BASE_URL}/api/v1/images`,
};

// Helper function to get product image URL
export const getProductImageUrl = (productId) => {
  if (!productId) return null;
  return `${config.IMAGES_URL}/${productId}`;
};

// Helper function to get fallback image URL (komo)
export const getFallbackImageUrl = () => {
  return `${config.IMAGES_URL}/komo`;
};

export default config;