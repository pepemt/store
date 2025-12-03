import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, ChevronRight, Truck, Shield, Star, ArrowRight } from 'lucide-react'
import { productService } from '../services/productService'
import { useAuth } from '../context/AuthContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'

import {
  CategoryGrid,
  Bestsellers,
  DepartmentCards,
  NewArrivals,
  PromoBanner,
  Testimonials,
  Newsletter,
} from '../components/landing'

interface Product {
  id: string | number
  name?: string
  title?: string
  description?: string
  price: number
  images?: string[]
  rating?: number
  stock?: number
}

// --------- HERO CAROUSEL ---------

function HeroCarousel() {
  const navigate = useNavigate()
  const [currentSlide, setCurrentSlide] = useState(0)

  const slides = [
    {
      id: 1,
      title: "Bienvenido a Zenith",
      subtitle: "Descubre productos increíbles al mejor precio. Tu tienda de confianza con la mejor calidad y servicio.",
      primaryButton: "Crear cuenta gratis",
      secondaryButton: "Iniciar sesión",
      primaryLink: "/signup",
      secondaryLink: "/login",
      bgColor: "#6e348d"
    },
    {
      id: 2,
      title: "Ofertas Especiales",
      subtitle: "No te pierdas nuestras promociones exclusivas. Descuentos increíbles en productos seleccionados.",
      primaryButton: "Ver ofertas",
      secondaryButton: "Explorar catálogo",
      primaryLink: "/products",
      secondaryLink: "/products",
      bgColor: "#6e348d"
    },
    {
      id: 3,
      title: "Envío Gratis",
      subtitle: "Disfruta de envío gratuito en compras mayores a $500. Recibe tus productos en la comodidad de tu hogar.",
      primaryButton: "Comprar ahora",
      secondaryButton: "Más información",
      primaryLink: "/products",
      secondaryLink: "/products",
      bgColor: "#6e348d"
    }
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length)
    }, 5000)
    return () => clearInterval(interval)
  }, [slides.length])

  const nextSlide = () => setCurrentSlide((prev) => (prev + 1) % slides.length)
  const prevSlide = () => setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length)

  return (
    <section className="relative h-[500px] md:h-[600px] overflow-hidden">
      <AnimatePresence mode="wait">
        {slides.map((slide, index) => (
          index === currentSlide && (
            <motion.div
              key={slide.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.7 }}
              className="absolute inset-0"
            >
              <div
                className="h-full flex items-center justify-center text-white"
                style={{ backgroundColor: slide.bgColor }}
              >
                <div className="container mx-auto px-4 text-center">
                  <motion.h1
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.2 }}
                    className="mb-4 text-4xl md:text-6xl font-bold drop-shadow-xl"
                    style={{ textShadow: '2px 2px 8px rgba(0,0,0,0.3)' }}
                  >
                    {slide.title}
                  </motion.h1>
                  <motion.p
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.3 }}
                    className="mb-8 text-lg md:text-xl max-w-2xl mx-auto drop-shadow-lg"
                    style={{ textShadow: '1px 1px 4px rgba(0,0,0,0.3)' }}
                  >
                    {slide.subtitle}
                  </motion.p>
                  <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.4 }}
                    className="flex flex-col gap-4 sm:flex-row sm:justify-center"
                  >
                    <Button
                      size="lg"
                      variant="secondary"
                      onClick={() => navigate(slide.primaryLink)}
                      className="hover:bg-white font-semibold shadow-lg border-2 border-white"
                      style={{ backgroundColor: 'white', color: '#6e348d' }}
                    >
                      {slide.primaryButton}
                    </Button>
                    <Button
                      size="lg"
                      onClick={() => navigate(slide.secondaryLink)}
                      className="border-3 font-semibold shadow-lg backdrop-blur-sm hover:bg-white hover:text-[#6e348d] transition-all"
                      style={{ borderWidth: '3px', borderColor: 'white', backgroundColor: 'rgba(255,255,255,0.35)', color: 'white' }}
                    >
                      {slide.secondaryButton}
                    </Button>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          )
        ))}
      </AnimatePresence>

      {/* Navigation Buttons */}
      <Button
        variant="ghost"
        size="icon"
        onClick={prevSlide}
        className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/20 text-white backdrop-blur-sm hover:bg-white/30 hover:text-white h-12 w-12"
      >
        <ChevronLeft className="h-6 w-6" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={nextSlide}
        className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/20 text-white backdrop-blur-sm hover:bg-white/30 hover:text-white h-12 w-12"
      >
        <ChevronRight className="h-6 w-6" />
      </Button>

      {/* Indicators */}
      <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
        {slides.map((_, index) => (
          <button
            key={index}
            onClick={() => setCurrentSlide(index)}
            className={`h-2 rounded-full transition-all ${
              index === currentSlide ? 'w-8 bg-white' : 'w-2 bg-white/50'
            }`}
          />
        ))}
      </div>
    </section>
  )
}

// --------- FEATURES BAR ---------

function FeaturesBar() {
  const features = [
    {
      icon: Truck,
      title: "Envío Rápido",
      description: "Recibe tus productos en 24-48 horas",
      color: '#ffb320'
    },
    {
      icon: Star,
      title: "Calidad Premium",
      description: "Solo productos de la mejor calidad",
      color: '#6e348d'
    },
    {
      icon: Shield,
      title: "Garantía Total",
      description: "30 días de garantía en todos los productos",
      color: '#ffb320'
    }
  ]

  return (
    <section className="border-b border-gray-200 bg-gray-50 py-12">
      <div className="container mx-auto px-4">
        <div className="grid gap-8 md:grid-cols-3">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="text-center border-none shadow-md hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <motion.div
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg"
                    style={{ backgroundColor: feature.color }}
                  >
                    <feature.icon className="h-8 w-8" strokeWidth={2} />
                  </motion.div>
                  <h3 className="mb-2 text-xl font-semibold text-gray-900">{feature.title}</h3>
                  <p className="text-gray-600">{feature.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

// --------- PERSONALIZED RECOMMENDATIONS ---------

function PersonalizedRecommendations() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [recommendations, setRecommendations] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchRecommendations() {
      const customerId = user?.customer_id
      if (!customerId) {
        setRecommendations([])
        setLoading(false)
        return
      }

      try {
        const products = await productService.getRecommendationsForUser(customerId, 8)
        setRecommendations(products)
      } catch (err) {
        console.error('Error al cargar recomendaciones:', err)
        setRecommendations([])
      } finally {
        setLoading(false)
      }
    }
    fetchRecommendations()
  }, [user?.customer_id])

  if (!user || loading || recommendations.length === 0) {
    return null
  }

  const ProductCard = ({ p }: { p: Product }) => {
    const name = p.name || p.title || 'Producto'
    const image = p.images?.[0] || getProductImageUrl(String(p.id)) || getFallbackImageUrl()
    const fallbackImage = `https://picsum.photos/seed/${p.id}/800/600`
    return (
      <Link to={`/product/${p.id}`} className="group">
        <motion.div
          whileHover={{ y: -8, boxShadow: '0 20px 30px rgba(0,0,0,0.12)' }}
          transition={{ duration: 0.3 }}
        >
          <Card className="overflow-hidden transition-shadow hover:shadow-lg">
            <div className="relative aspect-square overflow-hidden bg-gray-100">
              <motion.img
                src={image}
                alt={name}
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
              {p.rating && (
                <Badge className="absolute right-2 top-2 bg-white text-gray-900 hover:bg-white shadow-sm">
                  <Star className="h-3 w-3 fill-yellow-400 text-yellow-400 mr-1" />
                  {p.rating}
                </Badge>
              )}
            </div>
            <CardHeader>
              <CardTitle className="line-clamp-2 text-base">{name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="line-clamp-2 text-sm text-gray-600">
                {p.description}
              </p>
            </CardContent>
            <CardFooter className="flex items-center justify-between">
              <span className="text-2xl font-bold" style={{ color: '#6e348d' }}>
                ${p.price ? p.price.toFixed(2) : '0.00'}
              </span>
            </CardFooter>
          </Card>
        </motion.div>
      </Link>
    )
  }

  return (
    <section className="py-16 bg-gradient-to-b from-purple-50 to-white">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-12 text-center"
        >
          <div className="inline-flex items-center gap-2 mb-2">
            <h2 className="text-3xl font-bold text-gray-900">Recomendados para ti</h2>
          </div>
          <p className="text-gray-600">Basado en tus compras recientes, {user.name?.split(' ')[0]}</p>
        </motion.div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {recommendations.map((p) => (
            <ProductCard key={p.id} p={p} />
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="mt-12 text-center"
        >
          <Button
            size="lg"
            onClick={() => navigate('/products')}
            className="inline-flex items-center gap-2 text-white shadow-lg hover:shadow-xl transition-shadow"
            style={{ backgroundColor: '#6e348d' }}
          >
            Ver más recomendaciones
            <ArrowRight className="h-5 w-5" strokeWidth={2} />
          </Button>
        </motion.div>
      </div>
    </section>
  )
}

// --------- MAIN LANDING PAGE ---------

export default function Landing() {
  useEffect(() => {
    if ("scrollRestoration" in window.history) {
      window.history.scrollRestoration = "manual"
    }
    window.scrollTo({ top: 0, behavior: "smooth" })
  }, [])

  return (
    <div className="min-h-screen bg-white">
      {/* 1. Hero Carousel */}
      <HeroCarousel />

      {/* 2. Features Bar */}
      <FeaturesBar />

      {/* 3. Category Grid (NUEVO - PRIORIDAD) */}
      <CategoryGrid />

      {/* 4. Bestsellers */}
      <Bestsellers />

      {/* 5. Shop by Department */}
      <DepartmentCards />

      {/* 6. New Arrivals */}
      <NewArrivals />

      {/* 7. Personalized Recommendations (si está logueado) */}
      <PersonalizedRecommendations />

      {/* 8. Promo Banner */}
      <PromoBanner />

      {/* 9. Testimonials */}
      <Testimonials />

      {/* 10. Newsletter */}
      <Newsletter />
    </div>
  )
}
