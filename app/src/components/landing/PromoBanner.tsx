import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Truck, Gift, Percent } from 'lucide-react'
import { Button } from '../ui/button'

export function PromoBanner() {
  const ref = useRef(null)
  const navigate = useNavigate()

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  })

  const y = useTransform(scrollYProgress, [0, 1], ['0%', '20%'])

  return (
    <section
      ref={ref}
      className="relative py-24 overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #6e348d 0%, #9b69b9 50%, #5a2a72 100%)',
      }}
    >
      {/* Pattern overlay con parallax */}
      <motion.div
        style={{ y }}
        className="absolute inset-0 pointer-events-none"
      >
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
      </motion.div>

      <div className="container mx-auto px-4 relative z-10">
        <div className="max-w-4xl mx-auto text-center">
          {/* Icons row */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="flex justify-center gap-8 md:gap-12 mb-8"
          >
            <motion.div
              whileHover={{ scale: 1.1, rotate: 5 }}
              className="flex flex-col items-center gap-3"
            >
              <div
                className="h-16 w-16 rounded-full flex items-center justify-center shadow-lg"
                style={{ backgroundColor: '#ffb320' }}
              >
                <Truck className="h-8 w-8 text-white" strokeWidth={2.5} />
              </div>
              <span className="text-sm font-bold text-white">
                Envío Express
              </span>
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.1, rotate: -5 }}
              className="flex flex-col items-center gap-3"
            >
              <div
                className="h-16 w-16 rounded-full flex items-center justify-center shadow-lg"
                style={{ backgroundColor: '#ffb320' }}
              >
                <Gift className="h-8 w-8 text-white" strokeWidth={2.5} />
              </div>
              <span className="text-sm font-bold text-white">
                Empaque Premium
              </span>
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.1, rotate: 5 }}
              className="flex flex-col items-center gap-3"
            >
              <div
                className="h-16 w-16 rounded-full flex items-center justify-center shadow-lg"
                style={{ backgroundColor: '#ffb320' }}
              >
                <Percent className="h-8 w-8 text-white" strokeWidth={2.5} />
              </div>
              <span className="text-sm font-bold text-white">
                Ofertas Exclusivas
              </span>
            </motion.div>
          </motion.div>

          {/* Main text */}
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl md:text-5xl font-bold mb-4 text-white drop-shadow-lg"
          >
            Envío Gratis
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-2xl md:text-3xl font-bold mb-4 drop-shadow-md"
            style={{ color: '#ffb320' }}
          >
            En compras mayores a $500
          </motion.p>
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-lg font-medium mb-8 max-w-2xl mx-auto text-white/90"
          >
            Disfruta de envío gratuito en tu próxima compra. Aplica en todo el catálogo
            y recibe tus productos en la comodidad de tu hogar.
          </motion.p>

          {/* CTA Button */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <Button
              size="lg"
              onClick={() => navigate('/products')}
              className="bg-white hover:bg-gray-100 font-semibold shadow-xl px-8 py-6 text-lg"
              style={{ color: '#6e348d' }}
            >
              Comprar Ahora
            </Button>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
