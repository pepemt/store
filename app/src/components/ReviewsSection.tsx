import { useState } from 'react'
import { Star, ChevronDown, ChevronUp, MessageSquare } from 'lucide-react'
import { useProductReviews } from '../hooks/useReviews'

interface ReviewsSectionProps {
  articleId: number
}

function StarRating({ rating, size = 'sm' }: { rating: number; size?: 'sm' | 'md' }) {
  const starSize = size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'

  return (
    <div className="flex items-center gap-0.5">
      {[...Array(5)].map((_, i) => (
        <Star
          key={i}
          className={`${starSize} ${
            i < Math.floor(rating)
              ? 'fill-yellow-400 text-yellow-400'
              : i < rating
              ? 'fill-yellow-400/50 text-yellow-400'
              : 'text-gray-300'
          }`}
        />
      ))}
    </div>
  )
}

export function ReviewsSection({ articleId }: ReviewsSectionProps) {
  const [expanded, setExpanded] = useState(false)
  const [page, setPage] = useState(1)
  const limit = expanded ? 10 : 3

  const { data, isLoading, error } = useProductReviews(articleId, { limit, page })

  if (isLoading) {
    return (
      <section className="mt-12 border-t border-gray-200 pt-8">
        <h2 className="mb-6 text-xl font-bold text-gray-900">Opiniones de Clientes</h2>
        <div className="animate-pulse space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-lg" />
          ))}
        </div>
      </section>
    )
  }

  if (error || !data) {
    return null
  }

  const { reviews, total, average_rating } = data

  if (total === 0) {
    return (
      <section className="mt-12 border-t border-gray-200 pt-8">
        <h2 className="mb-6 text-xl font-bold text-gray-900">Opiniones de Clientes</h2>
        <div className="text-center py-8 bg-gray-50 rounded-lg">
          <MessageSquare className="mx-auto h-12 w-12 text-gray-400 mb-3" />
          <p className="text-gray-500">Este producto aún no tiene opiniones.</p>
          <p className="text-sm text-gray-400 mt-1">Sé el primero en compartir tu experiencia.</p>
        </div>
      </section>
    )
  }

  return (
    <section className="mt-12 border-t border-gray-200 pt-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900">Opiniones de Clientes</h2>
        <div className="flex items-center gap-3">
          <StarRating rating={average_rating} size="md" />
          <span className="text-lg font-semibold text-gray-900">
            {average_rating.toFixed(1)}
          </span>
          <span className="text-gray-500">({total} opiniones)</span>
        </div>
      </div>

      {/* Rating distribution */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold" style={{ color: '#6e348d' }}>
              {average_rating.toFixed(1)}
            </div>
            <StarRating rating={average_rating} />
            <div className="text-sm text-gray-500 mt-1">{total} opiniones</div>
          </div>
          <div className="flex-1 space-y-1">
            {[5, 4, 3, 2, 1].map((stars) => {
              const count = reviews.filter((r) => r.review_stars === stars).length
              const percentage = total > 0 ? (count / total) * 100 : 0
              return (
                <div key={stars} className="flex items-center gap-2 text-sm">
                  <span className="w-3 text-gray-600">{stars}</span>
                  <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                  <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${percentage}%`,
                        backgroundColor: '#6e348d',
                      }}
                    />
                  </div>
                  <span className="w-8 text-gray-500 text-right">{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Reviews list */}
      <div className="space-y-4">
        {reviews.map((review) => (
          <div
            key={review.id}
            className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-sm transition-shadow"
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <StarRating rating={review.review_stars} />
                {review.date && (
                  <span className="text-xs text-gray-400 ml-2">
                    {new Date(review.date).toLocaleDateString('es-MX', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                )}
              </div>
              {review.cluster_label && (
                <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
                  {review.cluster_label.split('—')[0].trim()}
                </span>
              )}
            </div>
            <p className="text-gray-700 text-sm leading-relaxed">{review.review_text}</p>
          </div>
        ))}
      </div>

      {/* Expand/Collapse button */}
      {total > 3 && (
        <div className="mt-6 text-center">
          <button
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-2 px-6 py-2 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            style={{ color: '#6e348d' }}
          >
            {expanded ? (
              <>
                Ver menos <ChevronUp className="h-4 w-4" />
              </>
            ) : (
              <>
                Ver todas las opiniones ({total}) <ChevronDown className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      )}

      {/* Pagination for expanded view */}
      {expanded && total > limit && (
        <div className="mt-4 flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 text-sm border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Anterior
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Página {page} de {Math.ceil(total / limit)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / limit)}
            className="px-4 py-2 text-sm border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Siguiente
          </button>
        </div>
      )}
    </section>
  )
}

export default ReviewsSection
