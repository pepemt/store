import { useQuery, useMutation } from '@tanstack/react-query'
import { landingService } from '../services/landingService'

// Cache times
const FIVE_MINUTES = 5 * 60 * 1000
const TEN_MINUTES = 10 * 60 * 1000

/**
 * Hook para obtener categorías con imágenes.
 */
export function useCategoriesWithImages(limit: number = 8) {
  return useQuery({
    queryKey: ['landing', 'categories', limit],
    queryFn: () => landingService.getCategoriesWithImages(limit),
    staleTime: FIVE_MINUTES,
    gcTime: TEN_MINUTES,
  })
}

/**
 * Hook para obtener departamentos con imágenes.
 */
export function useDepartmentsWithImages(limit: number = 6) {
  return useQuery({
    queryKey: ['landing', 'departments', limit],
    queryFn: () => landingService.getDepartmentsWithImages(limit),
    staleTime: FIVE_MINUTES,
    gcTime: TEN_MINUTES,
  })
}

/**
 * Hook para obtener productos más vendidos.
 */
export function useBestsellers(limit: number = 8) {
  return useQuery({
    queryKey: ['landing', 'bestsellers', limit],
    queryFn: () => landingService.getBestsellers(limit),
    staleTime: FIVE_MINUTES,
    gcTime: TEN_MINUTES,
  })
}

/**
 * Hook para obtener productos nuevos.
 */
export function useNewArrivals(limit: number = 8) {
  return useQuery({
    queryKey: ['landing', 'newArrivals', limit],
    queryFn: () => landingService.getNewArrivals(limit),
    staleTime: FIVE_MINUTES,
    gcTime: TEN_MINUTES,
  })
}

/**
 * Hook para obtener reviews destacados.
 */
export function useFeaturedReviews(limit: number = 6) {
  return useQuery({
    queryKey: ['landing', 'reviews', limit],
    queryFn: () => landingService.getFeaturedReviews(limit),
    staleTime: FIVE_MINUTES,
    gcTime: TEN_MINUTES,
  })
}

/**
 * Hook para obtener el banner promocional.
 */
export function usePromoBanner() {
  return useQuery({
    queryKey: ['landing', 'promoBanner'],
    queryFn: () => landingService.getPromoBanner(),
    staleTime: TEN_MINUTES,
    gcTime: TEN_MINUTES * 2,
  })
}

/**
 * Hook para suscribirse al newsletter.
 */
export function useNewsletterSubscription() {
  return useMutation({
    mutationFn: (email: string) => landingService.subscribeNewsletter(email),
  })
}
