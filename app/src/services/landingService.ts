/**
 * Servicio para los endpoints de la landing page.
 */

import { config } from '../config/api'

const API_BASE = config.BASE_URL

// --------- TIPOS ---------

export interface CategoryWithImage {
  name: string
  slug: string
  image_url: string
  product_count: number
  representative_product_id: number
}

export interface DepartmentWithImage {
  name: string
  slug: string
  image_url: string
  product_count: number
}

export interface LandingProduct {
  id: number
  name: string
  description?: string
  category?: string
  department?: string
  price: number
  stock: number
  rating: number
  images: string[]
  color_group?: string
  product_type?: string
  sales_count?: number
}

export interface FeaturedReview {
  product_id: number
  product_name: string
  product_image: string
  reviewer_name: string
  review_text: string
  rating: number
}

export interface PromoBanner {
  title: string
  subtitle: string
  description: string
  cta_text: string
  cta_link: string
  background_color: string
  accent_color: string
}

// --------- SERVICIOS ---------

export const landingService = {
  /**
   * Obtiene categorías con imágenes representativas.
   */
  async getCategoriesWithImages(limit: number = 8): Promise<CategoryWithImage[]> {
    const response = await fetch(`${API_BASE}/api/v1/landing/categories-with-images?limit=${limit}`)
    if (!response.ok) {
      throw new Error('Error al obtener categorías')
    }
    const data = await response.json()
    return data.categories
  },

  /**
   * Obtiene departamentos con imágenes representativas.
   */
  async getDepartmentsWithImages(limit: number = 6): Promise<DepartmentWithImage[]> {
    const response = await fetch(`${API_BASE}/api/v1/landing/departments-with-images?limit=${limit}`)
    if (!response.ok) {
      throw new Error('Error al obtener departamentos')
    }
    const data = await response.json()
    return data.departments
  },

  /**
   * Obtiene los productos más vendidos.
   */
  async getBestsellers(limit: number = 8): Promise<LandingProduct[]> {
    const response = await fetch(`${API_BASE}/api/v1/landing/bestsellers?limit=${limit}`)
    if (!response.ok) {
      throw new Error('Error al obtener bestsellers')
    }
    const data = await response.json()
    return data.products
  },

  /**
   * Obtiene los productos más recientes.
   */
  async getNewArrivals(limit: number = 8): Promise<LandingProduct[]> {
    const response = await fetch(`${API_BASE}/api/v1/landing/new-arrivals?limit=${limit}`)
    if (!response.ok) {
      throw new Error('Error al obtener nuevos productos')
    }
    const data = await response.json()
    return data.products
  },

  /**
   * Obtiene reviews destacados para testimonios.
   */
  async getFeaturedReviews(limit: number = 6): Promise<FeaturedReview[]> {
    const response = await fetch(`${API_BASE}/api/v1/landing/featured-reviews?limit=${limit}`)
    if (!response.ok) {
      throw new Error('Error al obtener reviews')
    }
    const data = await response.json()
    return data.reviews
  },

  /**
   * Obtiene la información del banner promocional.
   */
  async getPromoBanner(): Promise<PromoBanner> {
    const response = await fetch(`${API_BASE}/api/v1/landing/promo-banner`)
    if (!response.ok) {
      throw new Error('Error al obtener banner')
    }
    return response.json()
  },

  /**
   * Suscribe un email al newsletter.
   */
  async subscribeNewsletter(email: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/api/v1/landing/newsletter/subscribe`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    })
    if (!response.ok) {
      throw new Error('Error al suscribir')
    }
    return response.json()
  },
}
