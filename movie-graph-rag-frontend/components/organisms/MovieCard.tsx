'use client'

import { useState } from 'react'
import Image from 'next/image'
import { Heart, Film, Star, Info } from 'lucide-react'
import { ScoreBar } from '@/components/atoms/ScoreBar'
import { SerendipityBadge } from '@/components/atoms/SerendipityBadge'
import { Tag } from '@/components/atoms/Tag'
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
  compatibilityScore?: number
  serendipityScore?: number
  director?: string | null
}

export interface MovieCardProps {
  movie: MovieCardMovie
  /** w-44 for carousel, w-64 for grid */
  size?: 'carousel' | 'grid'
  isFavorite?: boolean
  onToggleFavorite?: (movie: MovieCardMovie) => void
  onViewDetails?: (movie: MovieCardMovie) => void
  className?: string
}

export function MovieCard({
  movie,
  size = 'grid',
  isFavorite = false,
  onToggleFavorite,
  onViewDetails,
  className,
}: MovieCardProps) {
  const [imgError, setImgError] = useState(false)

  const posterUrl = movie.posterUrl?.startsWith('/')
    ? `https://image.tmdb.org/t/p/w500${movie.posterUrl}`
    : movie.posterUrl

  const hasPoster = Boolean(posterUrl && !imgError)
  const genre = movie.genres?.[0] ?? movie.genreName
  const year = movie.year ?? (movie.releaseDate ? Number(movie.releaseDate) || null : null)
  const rating = movie.rating ?? movie.averageRating
  const hasScore = typeof movie.compatibilityScore === 'number'
  const scorePercent = hasScore ? Math.round((movie.compatibilityScore ?? 0) * 100) : null

  const sizeClasses = { carousel: 'w-44', grid: 'w-full' }

  return (
    <div
      className={cn(
        'group relative flex flex-col rounded-xl overflow-hidden',
        'bg-surface border border-border',
        'transition-all duration-300',
        'hover:scale-[1.04] hover:-translate-y-1 hover:border-accent/40',
        'hover:shadow-[0_8px_32px_rgba(232,160,64,0.15)]',
        sizeClasses[size],
        className
      )}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] bg-surface2 overflow-hidden">
        {hasPoster ? (
          <Image
            src={posterUrl as string}
            alt={`Póster de ${movie.title}`}
            fill
            sizes="(max-width: 640px) 176px, 256px"
            className="object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <Film className="w-10 h-10 text-muted/30" />
          </div>
        )}

        {/* SerendipityBadge */}
        {typeof movie.serendipityScore === 'number' && (
          <SerendipityBadge score={movie.serendipityScore} position="top-left" />
        )}

        {/* Compat badge */}
        {scorePercent !== null && (
          <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded-md bg-bg/80 backdrop-blur-sm text-xs font-bold text-teal border border-teal/30">
            {scorePercent}%
          </div>
        )}

        {/* Fav button */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onToggleFavorite?.(movie) }}
          aria-label={isFavorite ? 'Quitar de favoritos' : 'Agregar a favoritos'}
          className={cn(
            'absolute bottom-2 right-2',
            'w-7 h-7 rounded-full flex items-center justify-center',
            'bg-bg/70 backdrop-blur-sm border border-border2',
            'transition-colors duration-200',
            isFavorite ? 'text-accent border-accent/40' : 'text-muted hover:text-accent'
          )}
        >
          <Heart className={cn('w-3.5 h-3.5', isFavorite && 'fill-current')} />
        </button>

        {/* Hover overlay CTA */}
        <div className={cn(
          'absolute inset-0 flex items-center justify-center',
          'bg-bg/60 backdrop-blur-sm',
          'opacity-0 group-hover:opacity-100 transition-opacity duration-200'
        )}>
          <button
            type="button"
            onClick={() => onViewDetails?.(movie)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent2 text-bg text-xs font-semibold hover:bg-accent2/90 transition-colors"
          >
            <Info className="w-3.5 h-3.5" />
            Ver detalles
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="flex flex-col gap-1.5 p-2.5">
        <h3 className="text-sm font-semibold text-text leading-tight line-clamp-2">
          {movie.title}
        </h3>

        <div className="flex items-center gap-1.5 flex-wrap">
          {genre && <Tag label={genre} size="sm" />}
          {year && <span className="text-[11px] text-muted">{year}</span>}
        </div>

        {rating !== null && rating !== undefined && (
          <div className="flex items-center gap-1 text-[11px] text-muted">
            <Star className="w-3 h-3 text-accent fill-accent" />
            <span>{rating.toFixed(1)}</span>
          </div>
        )}

        {/* ScoreBar at bottom */}
        {hasScore && (
          <ScoreBar
            score={movie.compatibilityScore ?? 0}
            animated
            variant="gradient"
            className="mt-1"
          />
        )}
      </div>
    </div>
  )
}
