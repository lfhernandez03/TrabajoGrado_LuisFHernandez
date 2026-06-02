'use client'

import { useState } from 'react'
import Image from 'next/image'
import { Heart, Film, Star, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface MovieCardMovie {
  uri?: string
  title: string
  posterUrl?: string | null
  year?: number | null
  releaseDate?: string | null
  runtime?: number | null
  genres?: string[]
  genreName?: string | null
  rating?: number | null
  averageRating?: number | null
  certification?: string | null
  description?: string | null
  compatibilityScore?: number
  serendipityScore?: number
  director?: string | null
}

export interface MovieCardProps {
  movie: MovieCardMovie
  isFavorite?: boolean
  onToggleFavorite?: (movie: MovieCardMovie) => void
  onViewDetails?: (movie: MovieCardMovie) => void
  onFindSimilar?: (movie: MovieCardMovie) => void
  className?: string
}

export function MovieCard({
  movie,
  isFavorite = false,
  onToggleFavorite,
  onViewDetails,
  onFindSimilar,
  className,
}: MovieCardProps) {
  const [imgError, setImgError] = useState(false)

  const posterUrl = movie.posterUrl?.startsWith('/')
    ? `https://image.tmdb.org/t/p/w500${movie.posterUrl}`
    : movie.posterUrl

  const hasPoster = Boolean(posterUrl && !imgError)
  const genre = movie.genres?.[0] ?? movie.genreName
  const year = movie.year ?? (movie.releaseDate ? new Date(movie.releaseDate).getFullYear() || null : null)
  const rating = movie.rating ?? movie.averageRating
  const hasRating = typeof rating === 'number'
  const formattedRuntime = movie.runtime
    ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
    : null

  return (
    <div
      onClick={() => onViewDetails?.(movie)}
      className={cn(
        'group relative overflow-hidden rounded-xl',
        'border border-white/15',
        'transition-all duration-300',
        'hover:scale-[1.02] hover:-translate-y-1',
        'hover:border-white/25 hover:shadow-2xl hover:shadow-black/70',
        onViewDetails && 'cursor-pointer',
        className
      )}
    >
      {/* Background: dark base + blurred poster on top */}
      <div className="absolute inset-0 bg-surface pointer-events-none" />
      {hasPoster && (
        <div className="absolute inset-0 pointer-events-none">
          <Image
            src={posterUrl as string}
            alt=""
            aria-hidden="true"
            fill
            sizes="100vw"
            className="object-cover scale-110 blur-xl opacity-30"
          />
        </div>
      )}

      {/* Card content — glass panel */}
      <div className="relative flex gap-5 min-h-48 p-5 bg-bg/30 backdrop-blur-[1px]">

        {/* Poster thumbnail */}
        <div className="relative w-28 shrink-0 rounded-lg shadow-xl overflow-hidden ring-1 ring-white/10">
          {hasPoster ? (
            <Image
              src={posterUrl as string}
              alt={`Poster of ${movie.title}`}
              fill
              sizes="128px"
              className="object-cover w-full h-full"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="h-full min-h-40 flex items-center justify-center bg-surface2">
              <Film className="w-10 h-10 text-muted/40" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 flex flex-col justify-between">

          {/* Title + action buttons */}
          <div className="flex items-start justify-between gap-3 mb-1">
            <h3 className="font-bold text-xl leading-snug line-clamp-2 text-text pr-1">
              {movie.title}
            </h3>
            <div className="shrink-0 flex items-center gap-1.5">
              {onFindSimilar && (
                <ActionButton
                  onClick={() => onFindSimilar(movie)}
                  aria-label={`Find similar to ${movie.title}`}
                  colorClass="hover:bg-teal/15 hover:text-teal hover:border-teal/40"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                </ActionButton>
              )}
              <ActionButton
                onClick={() => onToggleFavorite?.(movie)}
                aria-label={isFavorite ? `Remove ${movie.title} from favorites` : `Add ${movie.title} to favorites`}
                colorClass={
                  isFavorite
                    ? 'bg-accent2/15 text-accent2 border-accent2/40'
                    : 'hover:bg-accent2/15 hover:text-accent2 hover:border-accent2/40'
                }
              >
                <Heart className={cn('h-3.5 w-3.5', isFavorite && 'fill-current')} />
              </ActionButton>
            </div>
          </div>

          {/* Year · Runtime */}
          <p className="text-xs text-muted mb-3">
            {year ?? '—'}
            {formattedRuntime && <span> · {formattedRuntime}</span>}
          </p>

          {/* Rating · Certification · Genre */}
          <div className="flex items-center gap-1.5 mb-2.5 flex-wrap">
            {hasRating && (
              <>
                <Star className="h-3.5 w-3.5 text-accent fill-accent shrink-0" />
                <span className="text-sm font-semibold text-text">{rating!.toFixed(1)}</span>
              </>
            )}
            {movie.certification && (
              <>
                {hasRating && <span className="text-muted/50">·</span>}
                <span className="text-xs text-muted">{movie.certification}</span>
              </>
            )}
            {genre && (
              <>
                <span className="text-muted/50">·</span>
                <span className="text-xs text-muted">{genre}</span>
              </>
            )}
          </div>

          {/* Description */}
          {movie.description && (
            <p className="text-xs leading-relaxed text-muted/80 line-clamp-3">
              {movie.description}
            </p>
          )}

          {/* Director */}
          {movie.director && (
            <p className="mt-auto pt-3 text-xs text-muted/60">
              Dir. <span className="text-muted">{movie.director}</span>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// Small circular icon button

interface ActionButtonProps {
  onClick: () => void
  'aria-label': string
  colorClass: string
  children: React.ReactNode
}

function ActionButton({ onClick, 'aria-label': ariaLabel, colorClass, children }: ActionButtonProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-full',
        'bg-bg/50 backdrop-blur-sm border border-white/10',
        'text-muted transition-all duration-200',
        colorClass
      )}
    >
      {children}
    </button>
  )
}
