'use client'

import { MovieCard, type MovieCardMovie } from './MovieCard'
import { SkeletonMovieCard } from '@/components/atoms/Loader'
import { Film } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface MovieGridProps {
  movies: MovieCardMovie[]
  isLoading?: boolean
  skeletonCount?: number
  isFavorite?: (uri: string) => boolean
  onToggleFavorite?: (movie: MovieCardMovie) => void
  onViewDetails?: (movie: MovieCardMovie) => void
  onFindSimilar?: (movie: MovieCardMovie) => void
  emptyMessage?: string
  className?: string
}

export function MovieGrid({
  movies,
  isLoading = false,
  skeletonCount = 6,
  isFavorite,
  onToggleFavorite,
  onViewDetails,
  onFindSimilar,
  emptyMessage = 'No movies found matching those filters.',
  className,
}: MovieGridProps) {
  const gridClass = cn('grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3', className)

  if (isLoading) {
    return (
      <div className={gridClass}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <SkeletonMovieCard key={i} />
        ))}
      </div>
    )
  }

  if (movies.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center gap-3 py-24 text-center', className)}>
        <Film className="w-12 h-12 text-muted/30" />
        <p className="text-muted text-sm max-w-xs">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={gridClass}>
      {movies.map((movie, i) => (
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
  )
}
