import { config } from '../config/api';

/**
 * Product Service
 * Handles product listing, search, and details operations
 */

export const productService = {
  /**
   * Get products with pagination and filters
   * @param {Object} options - Query options
   * @param {number} options.page - Page number (default: 1)
   * @param {number} options.per_page - Items per page (default: 20)
   * @param {string} options.search - Search term
   * @param {string} options.category - Filter by category
   * @param {string} options.department - Filter by department
   * @returns {Promise<Object>} Products with pagination info
   */
  async getProducts(options = {}) {
    try {
      const { page = 1, per_page = 20, search, category, department } = options;
      
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: per_page.toString(),
      });
      
      if (search) params.append('search', search);
      if (category) params.append('category', category);
      if (department) params.append('department', department);

      const response = await fetch(`${config.PRODUCTS_URL}/?${params.toString()}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener productos');
      }

      return data;
    } catch (error) {
      console.error('Error al obtener productos:', error);
      throw error;
    }
  },

  /**
   * Search products quickly
   * @param {string} query - Search query
   * @param {number} limit - Result limit (default: 20)
   * @returns {Promise<Object>} Search results
   */
  async searchProducts(query, limit = 20) {
    try {
      const params = new URLSearchParams({
        q: query,
        limit: limit.toString(),
      });

      const response = await fetch(`${config.PRODUCTS_URL}/search?${params.toString()}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error en la búsqueda');
      }

      return data;
    } catch (error) {
      console.error('Error en búsqueda:', error);
      throw error;
    }
  },

  /**
   * Get product by ID
   * @param {number|string} productId - Product ID
   * @returns {Promise<Object>} Product details
   */
  async getProductById(productId) {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/${productId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Producto no encontrado');
      }

      return data;
    } catch (error) {
      console.error('Error al obtener producto:', error);
      throw error;
    }
  },

  /**
   * Get all categories
   * @returns {Promise<Array>} List of categories
   */
  async getCategories() {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/categories`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener categorías');
      }

      return data.categories || [];
    } catch (error) {
      console.error('Error al obtener categorías:', error);
      throw error;
    }
  },

  /**
   * Get all departments
   * @returns {Promise<Array>} List of departments
   */
  async getDepartments() {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/departments`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener departamentos');
      }

      return data.categories || [];
    } catch (error) {
      console.error('Error al obtener departamentos:', error);
      throw error;
    }
  },
};

export default productService;

