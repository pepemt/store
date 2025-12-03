import React, { useState } from 'react'
import { ChevronDown, ChevronUp, X } from 'lucide-react'

interface FilterOptions {
  categories: string[]
  colors: string[]
  product_types: string[]
  departments: string[]
  price_range: { min: number; max: number }
}

interface ActiveFilters {
  category?: string
  color_group?: string
  product_type?: string
  price_min?: number
  price_max?: number
}

interface FilterSidebarProps {
  filterOptions: FilterOptions | undefined
  isLoading: boolean
  activeFilters: ActiveFilters
  onFilterChange: (filters: ActiveFilters) => void
  onClearFilters: () => void
  onClose?: () => void
}

interface CollapsibleSectionProps {
  title: string
  isOpen: boolean
  onToggle: () => void
  children: React.ReactNode
}

function CollapsibleSection({ title, isOpen, onToggle, children }: CollapsibleSectionProps) {
  return (
    <div className="border-b border-gray-200 py-3">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="text-sm font-semibold text-gray-900">{title}</span>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-gray-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-500" />
        )}
      </button>
      {isOpen && <div className="mt-3">{children}</div>}
    </div>
  )
}

export default function FilterSidebar({
  filterOptions,
  isLoading,
  activeFilters,
  onFilterChange,
  onClearFilters,
  onClose,
}: FilterSidebarProps) {
  const [openSections, setOpenSections] = useState({
    category: true,
    color: true,
    price: true,
    productType: false,
  })

  const toggleSection = (section: keyof typeof openSections) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  const handleFilterClick = (key: keyof ActiveFilters, value: string | undefined) => {
    const newFilters = { ...activeFilters }
    if (newFilters[key] === value) {
      delete newFilters[key]
    } else {
      newFilters[key] = value as never
    }
    onFilterChange(newFilters)
  }

  const handlePriceChange = (min: number | undefined, max: number | undefined) => {
    onFilterChange({
      ...activeFilters,
      price_min: min,
      price_max: max,
    })
  }

  const activeCount = Object.values(activeFilters).filter((v) => v !== undefined).length

  if (isLoading) {
    return (
      <div className="w-full rounded-lg border border-gray-200 bg-white p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-24 rounded bg-gray-200" />
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-8 rounded bg-gray-100" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!filterOptions) return null

  return (
    <div className="w-full rounded-lg border border-gray-200 bg-white p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between border-b border-gray-200 pb-3">
        <h3 className="text-base font-bold text-gray-900">Filtros</h3>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <button
              onClick={onClearFilters}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
            >
              Limpiar ({activeCount})
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="rounded p-1 text-gray-500 hover:bg-gray-100 lg:hidden"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Categoria */}
      <CollapsibleSection
        title="Categoria"
        isOpen={openSections.category}
        onToggle={() => toggleSection('category')}
      >
        <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
          {filterOptions.categories.slice(0, 15).map((cat) => (
            <button
              key={cat}
              onClick={() => handleFilterClick('category', cat)}
              className="rounded-full px-2.5 py-1 text-xs font-medium transition-colors"
              style={{
                backgroundColor: activeFilters.category === cat ? '#6e348d' : '#f3f4f6',
                color: activeFilters.category === cat ? 'white' : '#374151',
              }}
            >
              {cat}
            </button>
          ))}
        </div>
      </CollapsibleSection>

      {/* Color */}
      <CollapsibleSection
        title="Color"
        isOpen={openSections.color}
        onToggle={() => toggleSection('color')}
      >
        <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
          {filterOptions.colors.map((color) => (
            <button
              key={color}
              onClick={() => handleFilterClick('color_group', color)}
              className="rounded-full px-2.5 py-1 text-xs font-medium transition-colors"
              style={{
                backgroundColor: activeFilters.color_group === color ? '#6e348d' : '#f3f4f6',
                color: activeFilters.color_group === color ? 'white' : '#374151',
              }}
            >
              {color}
            </button>
          ))}
        </div>
      </CollapsibleSection>

      {/* Precio */}
      <CollapsibleSection
        title="Precio"
        isOpen={openSections.price}
        onToggle={() => toggleSection('price')}
      >
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder="Min"
              value={activeFilters.price_min ?? ''}
              onChange={(e) =>
                handlePriceChange(
                  e.target.value ? Number(e.target.value) : undefined,
                  activeFilters.price_max
                )
              }
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-primary-600 focus:outline-none focus:ring-1 focus:ring-primary-600"
            />
            <span className="text-gray-400">-</span>
            <input
              type="number"
              placeholder="Max"
              value={activeFilters.price_max ?? ''}
              onChange={(e) =>
                handlePriceChange(
                  activeFilters.price_min,
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-primary-600 focus:outline-none focus:ring-1 focus:ring-primary-600"
            />
          </div>
          <p className="text-xs text-gray-500">
            Rango: ${filterOptions.price_range.min.toFixed(2)} - ${filterOptions.price_range.max.toFixed(2)}
          </p>
        </div>
      </CollapsibleSection>

      {/* Tipo de producto */}
      <CollapsibleSection
        title="Tipo de producto"
        isOpen={openSections.productType}
        onToggle={() => toggleSection('productType')}
      >
        <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
          {filterOptions.product_types.slice(0, 20).map((type) => (
            <button
              key={type}
              onClick={() => handleFilterClick('product_type', type)}
              className="rounded-full px-2.5 py-1 text-xs font-medium transition-colors"
              style={{
                backgroundColor: activeFilters.product_type === type ? '#6e348d' : '#f3f4f6',
                color: activeFilters.product_type === type ? 'white' : '#374151',
              }}
            >
              {type}
            </button>
          ))}
        </div>
      </CollapsibleSection>
    </div>
  )
}
