import { motion, AnimatePresence, useInView } from 'framer-motion'
import { useRef, useState, useEffect } from 'react'
import { Star, ChevronLeft, ChevronRight, Quote } from 'lucide-react'
import { useFeaturedReviews } from '../../hooks/useLandingData'
import { Button } from '../ui/button'
import { SimpleImageWithFallback } from '../ui/image-with-fallback'

export function Testimonials() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const { data: reviews, isLoading, error } = useFeaturedReviews(6)
  const [currentIndex, setCurrentIndex] = useState(0)

  // Auto-rotate carousel
  useEffect(() => {
    if (!reviews?.length) return

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % reviews.length)
    }, 5000)

    return () => clearInterval(interval)
  }, [reviews?.length])

  const nextSlide = () => {
    if (reviews?.length) {
      setCurrentIndex((prev) => (prev + 1) % reviews.length)
    }
  }

  const prevSlide = () => {
    if (reviews?.length) {
      setCurrentIndex((prev) => (prev - 1 + reviews.length) % reviews.length)
    }
  }

  if (error || isLoading || !reviews?.length) {
    return null
  }

  const currentReview = reviews[currentIndex]

  return (
    <section ref={ref} className="py-12 bg-gray-50">
      <div className="container mx-auto px-4">
        <h2 className="text-2xl font-bold text-center mb-2 text-gray-900">
          Lo Que Dicen Nuestros Clientes
        </h2>
        <p className="text-gray-600 text-center text-sm mb-6">
          Miles de clientes satisfechos nos respaldan
        </p>

        <div className="max-w-3xl mx-auto relative">
          {/* Navigation buttons */}
          <Button
            variant="ghost"
            size="icon"
            onClick={prevSlide}
            className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 z-10 rounded-full bg-white shadow-lg hover:bg-gray-50 h-12 w-12 hidden md:flex"
          >
            <ChevronLeft className="h-6 w-6" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={nextSlide}
            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 z-10 rounded-full bg-white shadow-lg hover:bg-gray-50 h-12 w-12 hidden md:flex"
          >
            <ChevronRight className="h-6 w-6" />
          </Button>

          {/* Testimonial card */}
          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.4 }}
              className="bg-white rounded-2xl shadow-lg p-6 md:p-8"
            >
              <div className="flex flex-col md:flex-row gap-6 items-center">
                {/* Product image */}
                <div className="w-24 h-24 md:w-32 md:h-32 rounded-xl overflow-hidden shadow-md flex-shrink-0">
                  <SimpleImageWithFallback
                    src={currentReview.product_image}
                    alt={currentReview.product_name}
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Review content */}
                <div className="flex-1 text-center md:text-left">
                  <Quote className="h-8 w-8 text-[#6e348d]/20 mb-2 mx-auto md:mx-0" />

                  <p className="text-base md:text-lg text-gray-700 mb-4 italic leading-relaxed">
                    "{currentReview.review_text}"
                  </p>

                  {/* Rating stars */}
                  <div className="flex items-center justify-center md:justify-start gap-1 mb-3">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`h-4 w-4 ${
                          i < Math.floor(currentReview.rating)
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-gray-300'
                        }`}
                      />
                    ))}
                    <span className="ml-2 text-gray-600 text-sm font-medium">
                      {currentReview.rating.toFixed(1)}
                    </span>
                  </div>

                  {/* Reviewer info */}
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">
                      {currentReview.reviewer_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      Compró: {currentReview.product_name}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Dots indicator */}
          <div className="flex justify-center gap-2 mt-6">
            {reviews.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentIndex(index)}
                className={`h-2 rounded-full transition-all ${
                  index === currentIndex
                    ? 'w-6 bg-[#6e348d]'
                    : 'w-2 bg-gray-300 hover:bg-gray-400'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
