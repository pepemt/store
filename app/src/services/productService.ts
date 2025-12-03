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
  color_group?: string
  product_type?: string
  price_min?: number
  price_max?: number
}

interface FilterOptions {
  categories: string[]
  colors: string[]
  product_types: string[]
  departments: string[]
  price_range: { min: number; max: number }
}

interface UserRecommendation {
  user_id: string
  article_id: string
  score: number
}

interface ProductSimilarity {
  article_id: string
  score: number
}

export const productService = {
  async getProducts(options: GetProductsOptions = {}): Promise<ProductsResponse> {
    try {
      const {
        page = 1,
        per_page = 20,
        search,
        category,
        department,
        color_group,
        product_type,
        price_min,
        price_max,
      } = options

      const params = new URLSearchParams({
        page: page.toString(),
        per_page: per_page.toString(),
      })

      if (search) params.append('search', search)
      if (category) params.append('category', category)
      if (department) params.append('department', department)
      if (color_group) params.append('color_group', color_group)
      if (product_type) params.append('product_type', product_type)
      if (price_min !== undefined) params.append('price_min', price_min.toString())
      if (price_max !== undefined) params.append('price_max', price_max.toString())

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

  async getFilterOptions(): Promise<FilterOptions> {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/filters`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Error al obtener opciones de filtros')
      }

      return data
    } catch (error) {
      console.error('Error al obtener opciones de filtros:', error)
      throw error
    }
  },

  async getRecommendationsForUser(userId: string, limit = 10): Promise<Product[]> {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/recommend/user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, N: limit }),
      })

      // Manejar 404 como "sin recomendaciones" (no como error)
      if (response.status === 404) {
        return []
      }

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Error al obtener recomendaciones')
      }

      const recommendations: UserRecommendation[] = await response.json()

      // Si no hay recomendaciones, retornar vacío
      if (!recommendations || recommendations.length === 0) {
        return []
      }

      // Obtener los productos completos en paralelo
      const products = await Promise.all(
        recommendations.map(async (rec) => {
          try {
            return await this.getProductById(rec.article_id)
          } catch {
            return null
          }
        })
      )

      return products.filter((p): p is Product => p !== null)
    } catch (error) {
      console.error('Error al obtener recomendaciones:', error)
      // No relanzar - retornar vacío para no romper la UI
      return []
    }
  },

  async getSimilarProducts(articleId: string | number, limit = 10): Promise<Product[]> {
    try {
      const response = await fetch(`${config.PRODUCTS_URL}/similar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article_id: String(articleId), N: limit }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Error al obtener productos similares')
      }

      const similarities: ProductSimilarity[] = await response.json()

      // Obtener los productos completos en paralelo
      const products = await Promise.all(
        similarities.map(async (sim) => {
          try {
            return await this.getProductById(sim.article_id)
          } catch {
            return null
          }
        })
      )

      return products.filter((p): p is Product => p !== null)
    } catch (error) {
      console.error('Error al obtener productos similares:', error)
      throw error
    }
  },
}

export default productService
