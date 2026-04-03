'use client'

import { MovieCard, type MovieCardMovie } from './MovieCard'
import { SkeletonMovieCard } from '@/components/atoms/Loader'
import { Film } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface MovieGridProps {
  movies: MovieCardMovie[]
  isLoading?: boolean
  /** Number of skeleton cards to show while loading */
  skeletonCount?: number
  isFavorite?: (uri: string) => boolean
  onToggleFavorite?: (movie: MovieCardMovie) => void
  onViewDetails?: (movie: MovieCardMovie) => void
  emptyMessage?: string
  className?: string
}

export function MovieGrid({
  movies,
  isLoading = false,
  skeletonCount = 12,
  isFavorite,
  onToggleFavorite,
  onViewDetails,
  emptyMessage = 'No se encontraron películas con esos filtros.',
  className,
}: MovieGridProps) {

  if (isLoading) {
    return (
      <div className={cn(
        'grid gap-4',
        'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5',
        className
      )}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <SkeletonMovieCard key={i} />
        ))}
      </div>
    )
  }

  if (movies.length === 0) {
    return (
      <div className={cn(
        'flex flex-col items-center justify-center gap-3 py-24 text-center',
        className
      )}>
        <Film className="w-12 h-12 text-muted/30" />
        <p className="text-muted text-sm max-w-xs">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={cn(
      'grid gap-4',
      'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5',
      className
    )}>
      {movies.map((movie) => (
        <MovieCard
          key={movie.uri ?? movie.title}
          movie={movie}
          size="grid"
          isFavorite={isFavorite?.(movie.uri ?? '') ?? false}
          onToggleFavorite={onToggleFavorite}
          onViewDetails={onViewDetails}
        />
      ))}
    </div>
  )
}
