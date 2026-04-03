'use client'

import { useRef } from 'react'
import Link from 'next/link'
import { ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react'
import { MovieCard, type MovieCardMovie } from './MovieCard'
import { SkeletonMovieCard } from '@/components/atoms/Loader'
import { cn } from '@/lib/utils'

export interface RecommendationCarouselProps {
  title: string
  /** Subtitle shown in muted text next to the title */
  subtitle?: string
  movies: MovieCardMovie[]
  isLoading?: boolean
  /** Link for "Ver todo" button */
  viewAllHref?: string
  isFavorite?: (uri: string) => boolean
  onToggleFavorite?: (movie: MovieCardMovie) => void
  onViewDetails?: (movie: MovieCardMovie) => void
  /** Teal dot indicator before title */
  showLiveIndicator?: boolean
  className?: string
}

const SKELETON_COUNT = 6

export function RecommendationCarousel({
  title,
  subtitle,
  movies,
  isLoading = false,
  viewAllHref,
  isFavorite,
  onToggleFavorite,
  onViewDetails,
  showLiveIndicator = false,
  className,
}: RecommendationCarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const scroll = (dir: 'left' | 'right') => {
    if (!scrollRef.current) return
    const amount = 400
    scrollRef.current.scrollBy({ left: dir === 'right' ? amount : -amount, behavior: 'smooth' })
  }

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
          {/* Scroll arrows */}
          <button
            type="button"
            onClick={() => scroll('left')}
            aria-label="Anterior"
            className="w-8 h-8 rounded-full flex items-center justify-center bg-surface2 border border-border text-muted hover:text-text hover:border-border2 transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => scroll('right')}
            aria-label="Siguiente"
            className="w-8 h-8 rounded-full flex items-center justify-center bg-surface2 border border-border text-muted hover:text-text hover:border-border2 transition-all"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          {/* Ver todo */}
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

      {/* Scrollable row */}
      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto pb-2 scroll-smooth"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {isLoading
          ? Array.from({ length: SKELETON_COUNT }).map((_, i) => (
              <div key={i} className="w-44 shrink-0">
                <SkeletonMovieCard />
              </div>
            ))
          : movies.map((movie) => (
              <div key={movie.uri ?? movie.title} className="shrink-0 w-44">
                <MovieCard
                  movie={movie}
                  size="carousel"
                  isFavorite={isFavorite?.(movie.uri ?? '') ?? false}
                  onToggleFavorite={onToggleFavorite}
                  onViewDetails={onViewDetails}
                />
              </div>
            ))}
      </div>
    </section>
  )
}
