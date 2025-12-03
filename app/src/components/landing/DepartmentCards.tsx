import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { useDepartmentsWithImages } from '../../hooks/useLandingData'
import { fadeInUp } from './AnimatedSection'

interface DepartmentCardProps {
  department: {
    name: string
    slug: string
    image_url: string
    product_count: number
  }
  index: number
}

function DepartmentCard({ department, index }: DepartmentCardProps) {
  const isEven = index % 2 === 0
  const fallbackImage = `https://picsum.photos/seed/${department.slug}/800/600`

  return (
    <motion.div
      variants={fadeInUp}
      custom={index}
      className="group"
    >
      <Link
        to={`/products?department=${encodeURIComponent(department.name)}`}
        className={`flex flex-col sm:flex-row items-center gap-4 p-4 rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-xl ${
          isEven ? 'sm:flex-row' : 'sm:flex-row-reverse'
        }`}
        style={{ backgroundColor: isEven ? '#f8f5fa' : '#fff8e8' }}
      >
        <motion.div
          className="w-full sm:w-2/5 aspect-[3/2] rounded-xl overflow-hidden shadow-md"
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.3 }}
        >
          <img
            src={department.image_url}
            alt={department.name}
            className="h-full w-full object-cover"
            onError={(e) => {
              const target = e.target as HTMLImageElement
              if (target.src !== fallbackImage) {
                target.src = fallbackImage
              }
            }}
          />
        </motion.div>

        <div className={`w-full sm:w-3/5 text-center ${isEven ? 'sm:text-left' : 'sm:text-right'}`}>
          <h3 className="text-xl font-bold text-gray-900 mb-1">
            {department.name}
          </h3>
          <p className="text-gray-600 text-sm mb-2">
            {department.product_count.toLocaleString()} productos
          </p>
          <motion.div
            className={`inline-flex items-center gap-1 text-sm font-semibold transition-colors ${
              isEven ? 'text-[#6e348d]' : 'text-[#d4a017]'
            }`}
            whileHover={{ x: isEven ? 5 : -5 }}
          >
            {!isEven && <ArrowRight className="h-4 w-4 rotate-180" />}
            Explorar
            {isEven && <ArrowRight className="h-4 w-4" />}
          </motion.div>
        </div>
      </Link>
    </motion.div>
  )
}

function SkeletonCard() {
  return (
    <div className="animate-pulse flex flex-col md:flex-row items-center gap-6 p-6 rounded-3xl bg-gray-100">
      <div className="w-full md:w-1/2 aspect-[4/3] rounded-2xl bg-gray-200" />
      <div className="w-full md:w-1/2 space-y-4">
        <div className="h-8 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
        <div className="h-4 bg-gray-200 rounded w-1/3" />
      </div>
    </div>
  )
}

export function DepartmentCards() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const { data: departments, isLoading, error } = useDepartmentsWithImages(4)

  if (error || (!isLoading && !departments?.length)) {
    return null
  }

  return (
    <section ref={ref} className="py-12 bg-white">
      <div className="container mx-auto px-4 max-w-4xl">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-2xl font-bold text-center mb-2 text-gray-900"
        >
          Compra por Departamento
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-gray-600 text-center text-sm mb-6"
        >
          Encuentra el estilo perfecto para cada ocasión
        </motion.p>

        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={{
            hidden: {},
            visible: {
              transition: { staggerChildren: 0.1 },
            },
          }}
          className="space-y-4"
        >
          {isLoading
            ? [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
            : departments?.map((department, index) => (
                <DepartmentCard key={department.slug} department={department} index={index} />
              ))}
        </motion.div>
      </div>
    </section>
  )
}
