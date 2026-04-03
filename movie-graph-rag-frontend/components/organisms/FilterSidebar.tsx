'use client'

import { useState } from 'react'
import { X, RotateCcw, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tag } from '@/components/atoms/Tag'
import { cn } from '@/lib/utils'

// Genre list from FRONTEND_CONTEXT.md bridge ontology
const GENRES = [
  'Acción', 'Aventura', 'Animación', 'Comedia', 'Crimen',
  'Documental', 'Drama', 'Fantasía', 'Horror', 'Misterio',
  'Romance', 'Ciencia ficción', 'Thriller', 'Western',
]

const SORT_OPTIONS = [
  { value: 'rating', label: 'Mejor valoradas' },
  { value: 'year_desc', label: 'Más recientes' },
  { value: 'year_asc', label: 'Más antiguas' },
  { value: 'title', label: 'Alfabético' },
]

export interface FilterValues {
  genres: string[]
  director: string
  yearFrom: string
  yearTo: string
  runtimeMax: string
  sort: string
}

export const DEFAULT_FILTERS: FilterValues = {
  genres: [],
  director: '',
  yearFrom: '',
  yearTo: '',
  runtimeMax: '',
  sort: 'rating',
}

export interface FilterSidebarProps {
  filters: FilterValues
  onChange: (filters: FilterValues) => void
  onApply: () => void
  onReset: () => void
  /** Mobile: collapsed by default */
  className?: string
}

export function FilterSidebar({
  filters,
  onChange,
  onApply,
  onReset,
  className,
}: FilterSidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  const update = (key: keyof FilterValues, value: string | string[]) =>
    onChange({ ...filters, [key]: value })

  const toggleGenre = (genre: string) => {
    const next = filters.genres.includes(genre)
      ? filters.genres.filter((g) => g !== genre)
      : [...filters.genres, genre]
    update('genres', next)
  }

  const activeCount = [
    filters.genres.length > 0,
    filters.director.trim(),
    filters.yearFrom,
    filters.yearTo,
    filters.runtimeMax,
    filters.sort !== 'rating',
  ].filter(Boolean).length

  return (
    <>
      {/* Mobile toggle */}
      <div className="lg:hidden px-4 py-2">
        <button
          type="button"
          onClick={() => setMobileOpen((v) => !v)}
          className="flex items-center gap-2 text-sm text-muted hover:text-text transition-colors"
        >
          <SlidersHorizontal className="w-4 h-4" />
          Filtros
          {activeCount > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-teal/20 text-teal text-xs font-semibold">
              {activeCount}
            </span>
          )}
        </button>
      </div>

      {/* Sidebar panel */}
      <aside
        className={cn(
          'flex flex-col gap-6',
          'w-full lg:w-56 shrink-0',
          'lg:block',
          mobileOpen ? 'block' : 'hidden',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-muted" />
            <span className="text-sm font-semibold text-text">Filtros</span>
            {activeCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-teal/20 text-teal text-[11px] font-semibold">
                {activeCount}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onReset}
            className="text-muted hover:text-text transition-colors"
            aria-label="Limpiar filtros"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* ── Genre ── */}
        <FilterSection label="Género">
          <div className="flex flex-wrap gap-1.5">
            {GENRES.map((genre) => (
              <Tag
                key={genre}
                label={genre}
                variant="selectable"
                selected={filters.genres.includes(genre)}
                onToggle={toggleGenre}
                size="sm"
              />
            ))}
          </div>
        </FilterSection>

        {/* ── Sort ── */}
        <FilterSection label="Ordenar por">
          <div className="flex flex-col gap-1">
            {SORT_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => update('sort', value)}
                className={cn(
                  'flex items-center gap-2 px-2 py-1.5 rounded text-sm text-left transition-colors',
                  filters.sort === value
                    ? 'bg-teal/10 text-teal'
                    : 'text-muted hover:text-text hover:bg-surface2'
                )}
              >
                {filters.sort === value && <span className="text-teal">●</span>}
                {label}
              </button>
            ))}
          </div>
        </FilterSection>

        {/* ── Director ── */}
        <FilterSection label="Director">
          <div className="relative">
            <Input
              variant="search"
              value={filters.director}
              onChange={(e) => update('director', e.target.value)}
              placeholder="Ej. Nolan, Villeneuve…"
              className="text-sm pr-7"
            />
            {filters.director && (
              <button
                type="button"
                onClick={() => update('director', '')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-text"
                aria-label="Limpiar director"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </FilterSection>

        {/* ── Year ── */}
        <FilterSection label="Año">
          <div className="flex gap-2">
            <Input
              variant="default"
              type="number"
              value={filters.yearFrom}
              onChange={(e) => update('yearFrom', e.target.value)}
              placeholder="Desde"
              min={1900}
              max={2030}
              className="text-sm"
            />
            <Input
              variant="default"
              type="number"
              value={filters.yearTo}
              onChange={(e) => update('yearTo', e.target.value)}
              placeholder="Hasta"
              min={1900}
              max={2030}
              className="text-sm"
            />
          </div>
        </FilterSection>

        {/* ── Runtime ── */}
        <FilterSection label="Duración máxima">
          <div className="flex items-center gap-2">
            <Input
              variant="default"
              type="number"
              value={filters.runtimeMax}
              onChange={(e) => update('runtimeMax', e.target.value)}
              placeholder="minutos"
              min={30}
              max={300}
              className="text-sm"
            />
            <span className="text-xs text-muted shrink-0">min</span>
          </div>
        </FilterSection>

        {/* ── Apply ── */}
        <Button variant="primary" onClick={onApply} className="w-full">
          Aplicar filtros
        </Button>
      </aside>
    </>
  )
}

// ── Helper ────────────────────────────────────────────────────────────────────

function FilterSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold text-muted uppercase tracking-wider">{label}</p>
      {children}
    </div>
  )
}
