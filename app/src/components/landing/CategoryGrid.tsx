import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { useCategoriesWithImages } from '../../hooks/useLandingData'
import { staggerContainer, fadeInUp } from './AnimatedSection'
import { ImageWithFallback } from '../ui/image-with-fallback'

interface CategoryCardProps {
  category: {
    name: string
    slug: string
    image_url: string
    product_count: number
  }
}

function CategoryCard({ category }: CategoryCardProps) {
  return (
    <motion.div variants={fadeInUp}>
      <Link
        to={`/products?category=${encodeURIComponent(category.name)}`}
        className="group relative block aspect-square overflow-hidden rounded-2xl shadow-md"
      >
        <ImageWithFallback
          src={category.image_url}
          alt={category.name}
          className="h-full w-full object-cover"
          whileHover={{ scale: 1.1 }}
          transition={{ duration: 0.4 }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-4 transform transition-transform group-hover:translate-y-[-4px]">
          <h3 className="text-lg font-semibold text-white group-hover:underline decoration-2 underline-offset-2">
            {category.name}
          </h3>
          <p className="text-sm text-white/80">
            {category.product_count.toLocaleString()} productos
          </p>
        </div>
      </Link>
    </motion.div>
  )
}

function SkeletonCard() {
  return (
    <div className="aspect-square animate-pulse rounded-2xl bg-gray-200" />
  )
}

export function CategoryGrid() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const { data: categories, isLoading, error } = useCategoriesWithImages(8)

  if (error || (!isLoading && !categories?.length)) {
    return null
  }

  return (
    <section ref={ref} className="py-16 bg-gray-50">
      <div className="container mx-auto px-4">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-3xl font-bold text-center mb-4 text-gray-900"
        >
          Explora por Categoría
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-gray-600 text-center mb-12"
        >
          Encuentra lo que buscas en nuestras colecciones
        </motion.p>

        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : (
          <motion.div
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={staggerContainer}
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
          >
            {categories?.map((category) => (
              <CategoryCard key={category.slug} category={category} />
            ))}
          </motion.div>
        )}
      </div>
    </section>
  )
}
