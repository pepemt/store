import { motion, useInView } from 'framer-motion'
import { useRef, useState } from 'react'
import { Mail, Send, CheckCircle } from 'lucide-react'
import { useNewsletterSubscription } from '../../hooks/useLandingData'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { toast } from 'sonner'

export function Newsletter() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const [email, setEmail] = useState('')
  const [isSubscribed, setIsSubscribed] = useState(false)
  const { mutate: subscribe, isPending } = useNewsletterSubscription()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!email) {
      toast.error('Por favor ingresa tu email')
      return
    }

    subscribe(email, {
      onSuccess: (data) => {
        setIsSubscribed(true)
        setEmail('')
        toast.success(data.message)
      },
      onError: () => {
        toast.error('Error al suscribir. Intenta de nuevo.')
      },
    })
  }

  return (
    <section ref={ref} className="py-20" style={{ backgroundColor: '#6e348d' }}>
      <div className="container mx-auto px-4">
        <div className="max-w-2xl mx-auto text-center text-white">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <div className="h-20 w-20 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center mx-auto">
              {isSubscribed ? (
                <CheckCircle className="h-10 w-10" />
              ) : (
                <Mail className="h-10 w-10" />
              )}
            </div>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-3xl md:text-4xl font-bold mb-4"
          >
            {isSubscribed ? '¡Gracias por suscribirte!' : 'Únete a Nuestra Newsletter'}
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg text-white/80 mb-8"
          >
            {isSubscribed
              ? 'Pronto recibirás nuestras mejores ofertas y novedades en tu correo.'
              : 'Recibe ofertas exclusivas, novedades y descuentos especiales directamente en tu correo.'}
          </motion.p>

          {!isSubscribed && (
            <motion.form
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.3 }}
              onSubmit={handleSubmit}
              className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto"
            >
              <div className="relative flex-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <Input
                  type="email"
                  placeholder="tu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-12 bg-white border-0 text-gray-900 placeholder:text-gray-500 focus-visible:ring-2 focus-visible:ring-white/50"
                  disabled={isPending}
                />
              </div>
              <Button
                type="submit"
                size="lg"
                disabled={isPending}
                className="h-12 px-8 font-semibold shadow-lg"
                style={{ backgroundColor: '#ffb320', color: '#1a1a1a' }}
              >
                {isPending ? (
                  <span className="flex items-center gap-2">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 1 }}
                      className="h-5 w-5 border-2 border-current border-t-transparent rounded-full"
                    />
                    Enviando...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    Suscribirme
                    <Send className="h-4 w-4" />
                  </span>
                )}
              </Button>
            </motion.form>
          )}

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="text-sm text-white/60 mt-6"
          >
            No spam, solo contenido relevante. Puedes darte de baja cuando quieras.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
