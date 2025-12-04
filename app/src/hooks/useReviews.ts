import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { reviewService, ProductReviewsResponse, ReviewStats } from '../services/reviewService'

interface UseProductReviewsOptions {
  limit?: number
  page?: number
}

/**
 * Hook para obtener reviews de un producto con cache automático
 */
export function useProductReviews(
  articleId: number | undefined,
  options: UseProductReviewsOptions = {}
): UseQueryResult<ProductReviewsResponse, Error> {
  const { limit = 10, page = 1 } = options

  return useQuery({
    queryKey: ['reviews', 'product', articleId, { limit, page }],
    queryFn: () => reviewService.getProductReviews(articleId!, { limit, page }),
    enabled: !!articleId,
    staleTime: 5 * 60 * 1000, // Cache por 5 minutos
    gcTime: 10 * 60 * 1000, // Mantener en cache 10 minutos
  })
}

/**
 * Hook para obtener estadísticas de reviews de un producto
 */
export function useReviewStats(
  articleId: number | undefined
): UseQueryResult<ReviewStats, Error> {
  return useQuery({
    queryKey: ['reviews', 'stats', articleId],
    queryFn: () => reviewService.getReviewStats(articleId!),
    enabled: !!articleId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })
}
