import { config } from '../config/api';

/**
 * Authentication Service
 * Handles login, signup, and user information operations
 */

export const authService = {
  /**
   * Login user
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} User data with authentication info
   */
  async login(email, password) {
    try {
      const response = await fetch(`${config.AUTH_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error al iniciar sesión');
      }

      return data;
    } catch (error) {
      console.error('Error en login:', error);
      throw error;
    }
  },

  /**
   * Signup new user
   * @param {Object} userData - User registration data
   * @param {string} userData.name - User name
   * @param {string} userData.email - User email
   * @param {string} userData.password - User password
   * @param {number} userData.age - User age (optional)
   * @param {string} userData.postal_code - Postal code (default: "00000")
   * @returns {Promise<Object>} Created user data
   */
  async signupNew(userData) {
    try {
      const { name, email, password, age, postal_code = '00000' } = userData;
      
      const response = await fetch(`${config.AUTH_URL}/signup/new`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, password, age, postal_code }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error al crear cuenta');
      }

      return data;
    } catch (error) {
      console.error('Error en signup:', error);
      throw error;
    }
  },

  /**
   * Signup and link to existing customer
   * @param {Object} userData - User registration data
   * @param {string} userData.customer_id - Existing customer ID from Kaggle
   * @param {string} userData.name - User name
   * @param {string} userData.email - User email
   * @param {string} userData.password - User password
   * @returns {Promise<Object>} Linked user data
   */
  async signupLink(userData) {
    try {
      const { customer_id, name, email, password } = userData;
      
      const response = await fetch(`${config.AUTH_URL}/signup/link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ customer_id, name, email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error al vincular cuenta');
      }

      return data;
    } catch (error) {
      console.error('Error en signup vinculado:', error);
      throw error;
    }
  },

  /**
   * Get user information by customer ID
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} User information
   */
  async getUser(customerId) {
    try {
      const response = await fetch(`${config.AUTH_URL}/user/${customerId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error al obtener información del usuario');
      }

      return data;
    } catch (error) {
      console.error('Error al obtener usuario:', error);
      throw error;
    }
  },

  /**
   * Get unlinked customers (for linking accounts)
   * @param {number} limit - Limit of results (default: 10)
   * @param {number} offset - Offset for pagination (default: 0)
   * @returns {Promise<Array>} List of unlinked customers
   */
  async getUnlinkedCustomers(limit = 10, offset = 0) {
    try {
      const response = await fetch(
        `${config.AUTH_URL}/customers/unlinked?limit=${limit}&offset=${offset}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error al obtener clientes no vinculados');
      }

      return data;
    } catch (error) {
      console.error('Error al obtener clientes no vinculados:', error);
      throw error;
    }
  },
};

export default authService;

