import { useState, ImgHTMLAttributes } from 'react'
import { ImageOff } from 'lucide-react'
import { motion, HTMLMotionProps } from 'framer-motion'
import { cn } from '../../lib/utils'

interface ImageWithFallbackProps extends Omit<HTMLMotionProps<'img'>, 'onError'> {
  src?: string | null
  alt: string
  className?: string
  placeholderClassName?: string
}

export function ImageWithFallback({
  src,
  alt,
  className,
  placeholderClassName,
  ...props
}: ImageWithFallbackProps) {
  const [hasError, setHasError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const showPlaceholder = !src || hasError

  if (showPlaceholder) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-gray-100',
          className,
          placeholderClassName
        )}
      >
        <div className="flex flex-col items-center gap-2 text-gray-400">
          <ImageOff className="h-12 w-12" />
        </div>
      </div>
    )
  }

  return (
    <>
      {isLoading && (
        <div
          className={cn(
            'absolute inset-0 flex items-center justify-center bg-gray-100 animate-pulse',
            className
          )}
        />
      )}
      <motion.img
        src={src}
        alt={alt}
        className={cn(className, isLoading && 'opacity-0')}
        onLoad={() => setIsLoading(false)}
        onError={() => {
          setHasError(true)
          setIsLoading(false)
        }}
        {...props}
      />
    </>
  )
}

interface SimpleImageWithFallbackProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'onError' | 'src'> {
  src?: string | null
  alt: string
  className?: string
  placeholderClassName?: string
}

export function SimpleImageWithFallback({
  src,
  alt,
  className,
  placeholderClassName,
  ...props
}: SimpleImageWithFallbackProps) {
  const [hasError, setHasError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const showPlaceholder = !src || hasError

  if (showPlaceholder) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-gray-100',
          className,
          placeholderClassName
        )}
      >
        <div className="flex flex-col items-center gap-2 text-gray-400">
          <ImageOff className="h-12 w-12" />
        </div>
      </div>
    )
  }

  return (
    <>
      {isLoading && (
        <div
          className={cn(
            'absolute inset-0 flex items-center justify-center bg-gray-100 animate-pulse',
            className
          )}
        />
      )}
      <img
        src={src}
        alt={alt}
        className={cn(className, isLoading && 'opacity-0')}
        onLoad={() => setIsLoading(false)}
        onError={() => {
          setHasError(true)
          setIsLoading(false)
        }}
        {...props}
      />
    </>
  )
}
