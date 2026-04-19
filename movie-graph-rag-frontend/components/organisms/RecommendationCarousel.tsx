'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react'
import { MovieCard, type MovieCardMovie } from './MovieCard'
import { SkeletonMovieCard } from '@/components/atoms/Loader'
import { cn } from '@/lib/utils'

export interface RecommendationCarouselProps {
  title: string
  subtitle?: string
  movies: MovieCardMovie[]
  isLoading?: boolean
  viewAllHref?: string
  isFavorite?: (uri: string) => boolean
  onToggleFavorite?: (movie: MovieCardMovie) => void
  onViewDetails?: (movie: MovieCardMovie) => void
  onFindSimilar?: (movie: MovieCardMovie) => void
  showLiveIndicator?: boolean
  className?: string
}

const PAGE_SIZE = 3

export function RecommendationCarousel({
  title,
  subtitle,
  movies,
  isLoading = false,
  viewAllHref,
  isFavorite,
  onToggleFavorite,
  onViewDetails,
  onFindSimilar,
  showLiveIndicator = false,
  className,
}: RecommendationCarouselProps) {
  const [page, setPage] = useState(0)

  const totalPages = Math.max(1, Math.ceil(movies.length / PAGE_SIZE))
  const start = page * PAGE_SIZE
  const visible = movies.slice(start, start + PAGE_SIZE)

  const prev = () => setPage((p) => Math.max(0, p - 1))
  const next = () => setPage((p) => Math.min(totalPages - 1, p + 1))

  return (
    <section className={cn('flex flex-col gap-4', className)}>

      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          {showLiveIndicator && (
            <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse-dot" />
          )}
          <h2 className="font-display text-2xl text-text tracking-wide">{title}</h2>
          {subtitle && (
            <span className="text-sm text-muted hidden sm:block">— {subtitle}</span>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={prev}
            disabled={page === 0}
            aria-label="Anterior"
            className="w-8 h-8 rounded-full flex items-center justify-center bg-surface2 border border-border text-muted hover:text-text hover:border-border2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={next}
            disabled={page >= totalPages - 1}
            aria-label="Siguiente"
            className="w-8 h-8 rounded-full flex items-center justify-center bg-surface2 border border-border text-muted hover:text-text hover:border-border2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          {viewAllHref && (
            <Link
              href={viewAllHref}
              className="hidden sm:flex items-center gap-1 ml-2 text-xs text-muted hover:text-accent transition-colors"
            >
              Ver todo
              <ArrowRight className="w-3 h-3" />
            </Link>
          )}
        </div>
      </div>

      {/* Grid — same layout as MovieGrid */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3">
        {isLoading
          ? Array.from({ length: PAGE_SIZE }).map((_, i) => <SkeletonMovieCard key={i} />)
          : visible.map((movie, i) => (
              <MovieCard
                key={(movie.uri?.trim()) || (movie.title?.trim()) || `movie-${i}`}
                movie={movie}
                isFavorite={isFavorite?.(movie.uri ?? '') ?? false}
                onToggleFavorite={onToggleFavorite}
                onViewDetails={onViewDetails}
                onFindSimilar={onFindSimilar}
              />
            ))}
      </div>

      {/* Page dots */}
      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-1.5 pt-1">
          {Array.from({ length: totalPages }).map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setPage(i)}
              aria-label={`Página ${i + 1}`}
              className={cn(
                'rounded-full transition-all duration-200',
                i === page
                  ? 'w-4 h-1.5 bg-teal'
                  : 'w-1.5 h-1.5 bg-muted/30 hover:bg-muted/60'
              )}
            />
          ))}
        </div>
      )}
    </section>
  )
}
