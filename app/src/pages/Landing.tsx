import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Truck, Shield, Star, ArrowRight, Sparkles } from 'lucide-react'
import { productService } from '../services/productService'
import { useAuth } from '../context/AuthContext'
import { getProductImageUrl, getFallbackImageUrl } from '../config/api'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'

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

export default function Landing() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [featured, setFeatured] = useState<Product[]>([])
  const [featuredLoading, setFeaturedLoading] = useState(true)
  const [recommendations, setRecommendations] = useState<Product[]>([])
  const [recommendationsLoading, setRecommendationsLoading] = useState(false)
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

  useEffect(() => {
    async function fetchFeatured() {
      try {
        setFeaturedLoading(true)
        const data = await productService.getProducts({ page: 1, per_page: 8 })
        const items = data.products || []
        setFeatured(items.slice(0, 8))
      } catch (err) {
        console.error('Error al cargar destacados:', err)
      } finally {
        setFeaturedLoading(false)
      }
    }
    fetchFeatured()
  }, [])

  // Cargar recomendaciones personalizadas cuando hay usuario
  useEffect(() => {
    async function fetchRecommendations() {
      const customerId = user?.customer_id
      if (!customerId) {
        setRecommendations([])
        return
      }

      try {
        setRecommendationsLoading(true)
        const products = await productService.getRecommendationsForUser(customerId, 8)
        setRecommendations(products)
      } catch (err) {
        console.error('Error al cargar recomendaciones:', err)
        setRecommendations([])
      } finally {
        setRecommendationsLoading(false)
      }
    }
    fetchRecommendations()
  }, [user?.customer_id])

  useEffect(() => {
    if ("scrollRestoration" in window.history) {
      window.history.scrollRestoration = "manual"
    }

    window.scrollTo({
      top: 0,
      behavior: "smooth"
    })
  }, [])

  const nextSlide = () => setCurrentSlide((prev) => (prev + 1) % slides.length)
  const prevSlide = () => setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length)

  const ProductCard = ({ p }: { p: Product }) => {
    const name = p.name || p.title || 'Producto'
    const image = p.images?.[0] || getProductImageUrl(String(p.id)) || getFallbackImageUrl()
    return (
      <Link to={`/product/${p.id}`} className="group">
        <Card className="overflow-hidden transition-shadow hover:shadow-lg">
          <div className="relative aspect-square overflow-hidden bg-gray-100">
            <img
              src={image}
              alt={name}
              className="h-full w-full object-cover transition-transform group-hover:scale-110"
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
      </Link>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Hero Carousel */}
      <section className="relative h-[500px] overflow-hidden">
        {slides.map((slide, index) => (
          <div
            key={slide.id}
            className={`absolute inset-0 transition-opacity duration-1000 ${
              index === currentSlide ? 'opacity-100' : 'opacity-0 pointer-events-none'
            }`}
          >
            <div className="h-full flex items-center justify-center text-white shadow-inner" style={{ backgroundColor: slide.bgColor }}>
              <div className="container mx-auto px-4 text-center">
                <h1 className="mb-4 text-5xl font-bold md:text-6xl drop-shadow-xl" style={{ textShadow: '2px 2px 8px rgba(0,0,0,0.3)' }}>{slide.title}</h1>
                <p className="mb-8 text-lg md:text-xl max-w-2xl mx-auto drop-shadow-lg" style={{ textShadow: '1px 1px 4px rgba(0,0,0,0.3)' }}>{slide.subtitle}</p>
                <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
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
                </div>
              </div>
            </div>
          </div>
        ))}

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

      {/* Features */}
      <section className="border-b border-gray-200 bg-gray-50 py-12">
        <div className="container mx-auto px-4">
          <div className="grid gap-8 md:grid-cols-3">
            <Card className="text-center border-none shadow-md hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg" style={{ backgroundColor: '#ffb320' }}>
                  <Truck className="h-8 w-8" strokeWidth={2} />
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">Envío Rápido</h3>
                <p className="text-gray-600">Recibe tus productos en 24-48 horas</p>
              </CardContent>
            </Card>
            <Card className="text-center border-none shadow-md hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg" style={{ backgroundColor: '#6e348d' }}>
                  <Star className="h-8 w-8" strokeWidth={2} />
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">Calidad Premium</h3>
                <p className="text-gray-600">Solo productos de la mejor calidad</p>
              </CardContent>
            </Card>
            <Card className="text-center border-none shadow-md hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg" style={{ backgroundColor: '#ffb320' }}>
                  <Shield className="h-8 w-8" strokeWidth={2} />
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">Garantía Total</h3>
                <p className="text-gray-600">30 días de garantía en todos los productos</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Personalized Recommendations - Only for logged in users */}
      {user && (
        <section className="py-16 bg-gradient-to-b from-purple-50 to-white">
          <div className="container mx-auto px-4">
            <div className="mb-12 text-center">
              <div className="inline-flex items-center gap-2 mb-2">
                <Sparkles className="h-6 w-6" style={{ color: '#6e348d' }} />
                <h2 className="text-3xl font-bold text-gray-900">Recomendados para ti</h2>
                <Sparkles className="h-6 w-6" style={{ color: '#6e348d' }} />
              </div>
              <p className="text-gray-600">Productos seleccionados especialmente para ti, {user.name?.split(' ')[0]}</p>
            </div>

            {recommendationsLoading ? (
              <div className="text-center">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
                <p className="mt-4 text-gray-600">Cargando recomendaciones...</p>
              </div>
            ) : recommendations.length > 0 ? (
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {recommendations.map((p) => (
                  <ProductCard key={p.id} p={p} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">Explora más productos para obtener recomendaciones personalizadas</p>
                <Button
                  className="mt-4"
                  onClick={() => navigate('/products')}
                  style={{ backgroundColor: '#6e348d' }}
                >
                  Explorar productos
                </Button>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Featured Products */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <div className="mb-12 text-center">
            <h2 className="mb-2 text-3xl font-bold text-gray-900">Productos Destacados</h2>
            <p className="text-gray-600">Los favoritos de nuestros clientes</p>
          </div>

          {featuredLoading ? (
            <div className="text-center">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
              <p className="mt-4 text-gray-600">Cargando productos...</p>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {featured.map((p) => (
                <ProductCard key={p.id} p={p} />
              ))}
            </div>
          )}

          <div className="mt-12 text-center">
            <Button
              size="lg"
              onClick={() => navigate('/products')}
              className="inline-flex items-center gap-2 text-white shadow-lg hover:shadow-xl transition-shadow"
              style={{ backgroundColor: '#6e348d' }}
            >
              Ver todos los productos
              <ArrowRight className="h-5 w-5" strokeWidth={2} />
            </Button>
          </div>
        </div>
      </section>
    </div>
  )
}
