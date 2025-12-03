import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { productService } from '../services/productService'

interface Product {
  id: string | number
  name?: string
  title?: string
  description?: string
  price: number
  category?: string
  department?: string
  images?: string[]
  rating?: number
  stock?: number
  [key: string]: unknown
}

interface ProductsResponse {
  products: Product[]
  total: number
  page: number
  per_page: number
  total_pages: number
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

/**
 * Hook para obtener lista de productos con cache automático
 */
export function useProducts(options: GetProductsOptions = {}): UseQueryResult<ProductsResponse, Error> {
  const {
    page = 1,
    per_page = 12,
    search,
    category,
    department,
    color_group,
    product_type,
    price_min,
    price_max,
  } = options

  return useQuery({
    queryKey: ['products', { page, per_page, search, category, department, color_group, product_type, price_min, price_max }],
    queryFn: () => productService.getProducts(options),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })
}

/**
 * Hook para obtener un producto por ID con cache
 */
export function useProduct(productId: string | number | undefined): UseQueryResult<Product, Error> {
  return useQuery({
    queryKey: ['product', productId],
    queryFn: () => productService.getProductById(productId!),
    enabled: !!productId, // Solo ejecutar si hay ID
    staleTime: 10 * 60 * 1000, // Cache por 10 minutos (productos individuales cambian menos)
    gcTime: 30 * 60 * 1000, // Mantener en cache 30 minutos
  })
}

/**
 * Hook para obtener categorías con cache
 */
export function useCategories(): UseQueryResult<string[], Error> {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => productService.getCategories(),
    staleTime: 60 * 60 * 1000, // Cache por 1 hora (categorías casi nunca cambian)
    gcTime: 2 * 60 * 60 * 1000, // Mantener en cache 2 horas
  })
}

/**
 * Hook para búsqueda de productos con cache
 */
export function useSearchProducts(query: string, limit = 20) {
  return useQuery({
    queryKey: ['search', query, limit],
    queryFn: () => productService.searchProducts(query, limit),
    enabled: !!query && query.length > 0,
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  })
}

/**
 * Hook para obtener opciones de filtros con cache largo
 */
export function useFilterOptions(): UseQueryResult<FilterOptions, Error> {
  return useQuery({
    queryKey: ['filterOptions'],
    queryFn: () => productService.getFilterOptions(),
    staleTime: 60 * 60 * 1000, // Cache por 1 hora (filtros raramente cambian)
    gcTime: 2 * 60 * 60 * 1000,
  })
}
