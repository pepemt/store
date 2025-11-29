import { useState, useEffect, useRef, ImgHTMLAttributes } from 'react'

interface CachedImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  src: string
  fallbackSrc?: string
  cacheDuration?: number // en segundos, default: 7 días
  showPlaceholder?: boolean
}

const CACHE_NAME = 'zenith-images-v1'
const DEFAULT_CACHE_DURATION = 7 * 24 * 60 * 60 // 7 días en segundos

export default function CachedImage({
  src,
  fallbackSrc,
  cacheDuration = DEFAULT_CACHE_DURATION,
  showPlaceholder = true,
  alt = '',
  className = '',
  loading = 'lazy',
  ...props
}: CachedImageProps) {
  const [imageSrc, setImageSrc] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    loadImage()

    return () => {
      // Cleanup: revocar object URLs si existen
      if (imageSrc?.startsWith('blob:')) {
        URL.revokeObjectURL(imageSrc)
      }
    }
  }, [src])

  const loadImage = async () => {
    try {
      setIsLoading(true)
      setHasError(false)

      // 1. Verificar si la imagen está en cache del navegador
      const cachedBlob = await getCachedImage(src)

      if (cachedBlob) {
        // Cache HIT
        const objectUrl = URL.createObjectURL(cachedBlob)
        setImageSrc(objectUrl)
        setIsLoading(false)
        return
      }

      // 2. Cache MISS - Descargar la imagen
      const response = await fetch(src, {
        cache: 'force-cache', // Usar cache HTTP del navegador también
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const blob = await response.blob()

      // 3. Guardar en Cache API
      await cacheImage(src, blob, cacheDuration)

      // 4. Mostrar la imagen
      const objectUrl = URL.createObjectURL(blob)
      setImageSrc(objectUrl)
      setIsLoading(false)
    } catch (error) {
      console.error('Error loading image:', error)
      setHasError(true)
      setIsLoading(false)

      // Usar fallback si existe
      if (fallbackSrc) {
        setImageSrc(fallbackSrc)
      }
    }
  }

  const handleImageError = () => {
    setHasError(true)
    if (fallbackSrc && imageSrc !== fallbackSrc) {
      setImageSrc(fallbackSrc)
    }
  }

  // Si está cargando y se debe mostrar placeholder
  if (isLoading && showPlaceholder) {
    return (
      <div
        className={`animate-pulse bg-gray-200 ${className}`}
        style={{ aspectRatio: '1', ...props.style }}
      >
        <div className="flex h-full items-center justify-center">
          <svg
            className="h-10 w-10 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        </div>
      </div>
    )
  }

  // Si hay error y no hay fallback
  if (hasError && !imageSrc) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 ${className}`}
        style={{ aspectRatio: '1', ...props.style }}
      >
        <svg
          className="h-10 w-10 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </div>
    )
  }

  return (
    <img
      ref={imgRef}
      src={imageSrc || undefined}
      alt={alt}
      className={className}
      loading={loading}
      onError={handleImageError}
      {...props}
    />
  )
}

// Funciones helper para Cache API

async function getCachedImage(url: string): Promise<Blob | null> {
  try {
    // Verificar si Cache API está disponible
    if (!('caches' in window)) {
      return null
    }

    const cache = await caches.open(CACHE_NAME)
    const response = await cache.match(url)

    if (!response) {
      return null
    }

    // Verificar si el cache expiró
    const cachedTime = response.headers.get('X-Cached-Time')
    const cacheDuration = response.headers.get('X-Cache-Duration')

    if (cachedTime && cacheDuration) {
      const age = Date.now() - parseInt(cachedTime, 10)
      const maxAge = parseInt(cacheDuration, 10) * 1000

      if (age > maxAge) {
        // Cache expirado, eliminarlo
        await cache.delete(url)
        return null
      }
    }

    return await response.blob()
  } catch (error) {
    console.warn('Error getting cached image:', error)
    return null
  }
}

async function cacheImage(url: string, blob: Blob, duration: number): Promise<void> {
  try {
    // Verificar si Cache API está disponible
    if (!('caches' in window)) {
      return
    }

    const cache = await caches.open(CACHE_NAME)

    // Crear headers personalizados para tracking de expiración
    const headers = new Headers()
    headers.set('Content-Type', blob.type)
    headers.set('X-Cached-Time', Date.now().toString())
    headers.set('X-Cache-Duration', duration.toString())

    const response = new Response(blob, {
      status: 200,
      statusText: 'OK',
      headers,
    })

    await cache.put(url, response)
  } catch (error) {
    console.warn('Error caching image:', error)
  }
}

// Función para limpiar cache viejo
export async function clearOldImageCache(): Promise<void> {
  try {
    if (!('caches' in window)) {
      return
    }

    const cache = await caches.open(CACHE_NAME)
    const requests = await cache.keys()

    const now = Date.now()

    for (const request of requests) {
      const response = await cache.match(request)
      if (!response) continue

      const cachedTime = response.headers.get('X-Cached-Time')
      const cacheDuration = response.headers.get('X-Cache-Duration')

      if (cachedTime && cacheDuration) {
        const age = now - parseInt(cachedTime, 10)
        const maxAge = parseInt(cacheDuration, 10) * 1000

        if (age > maxAge) {
          await cache.delete(request)
        }
      }
    }
  } catch (error) {
    console.warn('Error clearing old cache:', error)
  }
}
