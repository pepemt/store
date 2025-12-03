import { motion, useInView } from 'framer-motion'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, Star, ChevronLeft, ChevronRight } from 'lucide-react'
import { useNewArrivals } from '../../hooks/useLandingData'
import { fadeInUp } from './AnimatedSection'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import type { LandingProduct } from '../../services/landingService'

interface ProductCardProps {
  product: LandingProduct
}

function ProductCard({ product }: ProductCardProps) {
  const image = product.images?.[0] || `https://picsum.photos/seed/${product.id}/800/600`
  const fallbackImage = `https://picsum.photos/seed/${product.id}/800/600`

  return (
    <motion.div variants={fadeInUp} className="min-w-[280px] max-w-[280px] flex-shrink-0">
      <Link to={`/product/${product.id}`} className="group block">
        <motion.div
          whileHover={{ y: -8, boxShadow: '0 20px 30px rgba(0,0,0,0.12)' }}
          transition={{ duration: 0.3 }}
        >
          <Card className="overflow-hidden border-none shadow-md">
            <div className="relative aspect-square overflow-hidden bg-gray-100">
              <motion.img
                src={image}
                alt={product.name}
                className="h-full w-full object-cover"
                whileHover={{ scale: 1.05 }}
                transition={{ duration: 0.4 }}
                onError={(e) => {
                  const target = e.target as HTMLImageElement
                  if (target.src !== fallbackImage) {
                    target.src = fallbackImage
                  }
                }}
              />
              <motion.div
                className="absolute left-2 top-2"
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
              >
                <Badge
                  className="gap-1 text-white shadow-lg"
                  style={{ backgroundColor: '#10b981' }}
                >
                  <Sparkles className="h-3 w-3" />
                  Nuevo
                </Badge>
              </motion.div>
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
            <CardFooter>
              <span className="text-2xl font-bold" style={{ color: '#6e348d' }}>
                ${product.price?.toFixed(2) || '0.00'}
              </span>
            </CardFooter>
          </Card>
        </motion.div>
      </Link>
    </motion.div>
  )
}

function SkeletonCard() {
  return (
    <div className="min-w-[280px] max-w-[280px] flex-shrink-0 animate-pulse">
      <div className="aspect-square rounded-lg bg-gray-200 mb-4" />
      <div className="h-4 bg-gray-200 rounded mb-2" />
      <div className="h-4 bg-gray-200 rounded w-2/3" />
    </div>
  )
}

export function NewArrivals() {
  const ref = useRef(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const { data: products, isLoading, error } = useNewArrivals(8)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(true)

  const checkScroll = () => {
    if (scrollRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current
      setCanScrollLeft(scrollLeft > 0)
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10)
    }
  }

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 300
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      })
      setTimeout(checkScroll, 300)
    }
  }

  if (error || (!isLoading && !products?.length)) {
    return null
  }

  return (
    <section ref={ref} className="py-12 bg-white">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-center gap-2 mb-2"
        >
          <Sparkles className="h-6 w-6 text-[#6e348d]" />
          <h2 className="text-2xl font-bold text-gray-900">Recién Llegados</h2>
        </motion.div>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-gray-600 text-center text-sm mb-8"
        >
          Las últimas novedades en nuestra tienda
        </motion.p>

        <div className="relative">
          {/* Scroll buttons */}
          {canScrollLeft && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => scroll('left')}
              className="absolute left-0 top-1/2 -translate-y-1/2 z-10 rounded-full bg-white/90 shadow-lg hover:bg-white h-12 w-12"
            >
              <ChevronLeft className="h-6 w-6" />
            </Button>
          )}
          {canScrollRight && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => scroll('right')}
              className="absolute right-0 top-1/2 -translate-y-1/2 z-10 rounded-full bg-white/90 shadow-lg hover:bg-white h-12 w-12"
            >
              <ChevronRight className="h-6 w-6" />
            </Button>
          )}

          {/* Carousel */}
          <motion.div
            ref={scrollRef}
            onScroll={checkScroll}
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={{
              hidden: {},
              visible: {
                transition: { staggerChildren: 0.08 },
              },
            }}
            className="flex gap-6 overflow-x-auto pb-4 scrollbar-hide scroll-smooth"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            {isLoading
              ? [...Array(8)].map((_, i) => <SkeletonCard key={i} />)
              : products?.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
          </motion.div>

          {/* Gradient overlays - solo mostrar izquierdo si ya se desplazó */}
          {canScrollLeft && (
            <div className="absolute left-0 top-0 bottom-4 w-8 bg-gradient-to-r from-white to-transparent pointer-events-none" />
          )}
          {canScrollRight && (
            <div className="absolute right-0 top-0 bottom-4 w-8 bg-gradient-to-l from-white to-transparent pointer-events-none" />
          )}
        </div>
      </div>
    </section>
  )
}
