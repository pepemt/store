import { config } from '../config/api'

interface Product {
  id: string | number
  name?: string
  title?: string
  description?: string
  price: number
  category?: string
  department?: string
  image?: string
  [key: string]: unknown
}

interface ProductsResponse {
  products: Product[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

interface SearchResponse {
  results: Product[]
  query: string
  total: number
}

interface GetProductsOptions {
  page?: number
  per_page?: number
  search?: string
  category?: string
  department?: string
}

export const productService = {
  async getProducts(options: GetProductsOptions = {}): Promise<ProductsResponse> {
    try {
      const { page = 1, per_page = 20, search, category, department } = options

      const params = new URLSearchParams({
        page: page.toString(),
        per_page: per_page.toString(),
      })

      if (search) params.append('search', search)
      if (category) params.append('category', category)
      if (department) params.append('department', department)

      const response = await fetch(`${config.PRODUCTS_URL}/?${params.toString()}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener productos')
      }

      return data
    } catch (error) {
      console.error('Error al obtener productos:', error)
      throw error
    }
  },

  async searchProducts(query: string, limit = 20): Promise<SearchResponse> {
    try {
      const params = new URLSearchParams({
        q: query,
        limit: limit.toString(),
      })

      const response = await fetch(`${config.PRODUCTS_URL}/search?${params.toString()}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Error en la búsqueda')
      }

      return data
    } catch (error) {
      console.error('Error en búsqueda:', error)
      throw error
    }
  },

  async getProductById(productId: number | string): Promise<Product> {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/${productId}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Producto no encontrado')
      }

      return data
    } catch (error) {
      console.error('Error al obtener producto:', error)
      throw error
    }
  },

  async getCategories(): Promise<string[]> {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/categories`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener categorías')
      }

      return data.categories || []
    } catch (error) {
      console.error('Error al obtener categorías:', error)
      throw error
    }
  },

  async getDepartments(): Promise<string[]> {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/departments`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener departamentos')
      }

      return data.categories || []
    } catch (error) {
      console.error('Error al obtener departamentos:', error)
      throw error
    }
  },
}

export default productService
