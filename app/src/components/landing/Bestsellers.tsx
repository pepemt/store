import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Flame, Star, ArrowRight } from 'lucide-react'
import { useBestsellers } from '../../hooks/useLandingData'
import { staggerContainer, fadeInUp } from './AnimatedSection'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { ImageWithFallback } from '../ui/image-with-fallback'
import type { LandingProduct } from '../../services/landingService'

interface ProductCardProps {
  product: LandingProduct
  index: number
}

function ProductCard({ product, index }: ProductCardProps) {
  const image = product.images?.[0]

  return (
    <motion.div variants={fadeInUp}>
      <Link to={`/product/${product.id}`} className="group block">
        <motion.div
          whileHover={{ y: -8, boxShadow: '0 20px 30px rgba(0,0,0,0.12)' }}
          transition={{ duration: 0.3 }}
        >
          <Card className="overflow-hidden border-none shadow-md">
            <div className="relative aspect-square overflow-hidden bg-gray-100">
              <ImageWithFallback
                src={image}
                alt={product.name}
                className="h-full w-full object-cover"
                whileHover={{ scale: 1.05 }}
                transition={{ duration: 0.4 }}
              />
              {index < 3 && (
                <Badge
                  className="absolute left-2 top-2 gap-1 text-white shadow-lg"
                  style={{ backgroundColor: '#ff6b35' }}
                >
                  <Flame className="h-3 w-3" />
                  Top {index + 1}
                </Badge>
              )}
              {product.rating && (
                <Badge className="absolute right-2 top-2 bg-white text-gray-900 hover:bg-white shadow-sm">
                  <Star className="h-3 w-3 fill-yellow-400 text-yellow-400 mr-1" />
                  {product.rating.toFixed(1)}
                </Badge>
              )}
            </div>
            <CardHeader className="pb-2">
              <CardTitle className="line-clamp-2 text-base group-hover:text-[#6e348d] transition-colors">
                {product.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="pb-2">
              <p className="line-clamp-2 text-sm text-gray-600">
                {product.description}
              </p>
            </CardContent>
            <CardFooter className="flex items-center justify-between">
              <span className="text-2xl font-bold" style={{ color: '#6e348d' }}>
                ${product.price?.toFixed(2) || '0.00'}
              </span>
              {product.sales_count && (
                <span className="text-xs text-gray-500">
                  {product.sales_count.toLocaleString()} vendidos
                </span>
              )}
            </CardFooter>
          </Card>
        </motion.div>
      </Link>
    </motion.div>
  )
}

function SkeletonCard() {
  return (
    <div className="animate-pulse">
      <div className="aspect-square rounded-lg bg-gray-200 mb-4" />
      <div className="h-4 bg-gray-200 rounded mb-2" />
      <div className="h-4 bg-gray-200 rounded w-2/3" />
    </div>
  )
}

export function Bestsellers() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const navigate = useNavigate()
  const { data: products, isLoading, error } = useBestsellers(8)

  if (error || (!isLoading && !products?.length)) {
    return null
  }

  return (
    <section ref={ref} className="py-16 bg-white">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-center gap-3 mb-4"
        >
          <Flame className="h-8 w-8 text-orange-500" />
          <h2 className="text-3xl font-bold text-gray-900">Los Más Vendidos</h2>
        </motion.div>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-gray-600 text-center mb-12"
        >
          Los favoritos de nuestros clientes
        </motion.p>

        {isLoading ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[...Array(8)].map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : (
          <motion.div
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={staggerContainer}
            className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
          >
            {products?.map((product, index) => (
              <ProductCard key={product.id} product={product} index={index} />
            ))}
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-12 text-center"
        >
          <Button
            size="lg"
            onClick={() => navigate('/products')}
            className="inline-flex items-center gap-2 text-white shadow-lg hover:shadow-xl transition-shadow"
            style={{ backgroundColor: '#6e348d' }}
          >
            Ver todos los productos
            <ArrowRight className="h-5 w-5" />
          </Button>
        </motion.div>
      </div>
    </section>
  )
}
