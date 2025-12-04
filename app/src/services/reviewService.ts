import { config } from '../config/api'

const REVIEWS_URL = `${config.BASE_URL}/api/v1/reviews`

export interface Review {
  id: number
  article_id: number
  review_text: string
  review_stars: number
  customer_id?: string
  date?: string
  cluster_label?: string
}

export interface ProductReviewsResponse {
  reviews: Review[]
  total: number
  average_rating: number
  page: number
  per_page: number
}

export interface ReviewStats {
  article_id: number
  total_reviews: number
  average_rating: number
}

export const reviewService = {
  async getProductReviews(
    articleId: number,
    options: { limit?: number; page?: number } = {}
  ): Promise<ProductReviewsResponse> {
    try {
      const { limit = 10, page = 1 } = options

      const params = new URLSearchParams({
        limit: limit.toString(),
        page: page.toString(),
      })

      const response = await fetch(
        `${REVIEWS_URL}/product/${articleId}?${params.toString()}`
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching product reviews:', error)
      return {
        reviews: [],
        total: 0,
        average_rating: 0,
        page: 1,
        per_page: 10,
      }
    }
  },

  async getReviewStats(articleId: number): Promise<ReviewStats> {
    try {
      const response = await fetch(`${REVIEWS_URL}/stats/${articleId}`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching review stats:', error)
      return {
        article_id: articleId,
        total_reviews: 0,
        average_rating: 0,
      }
    }
  },
}

export default reviewService
