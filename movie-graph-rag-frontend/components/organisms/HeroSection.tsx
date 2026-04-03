'use client'

import { useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { Sparkles, Film, Heart, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScoreBar } from '@/components/atoms/ScoreBar'
import { WhyCard } from '@/components/molecules/WhyCard'
import { SkeletonPoster, SkeletonBox } from '@/components/atoms/Loader'
import { cn } from '@/lib/utils'

// Quick-context chips from FRONTEND_CONTEXT.md MOOD_CHIPS
const QUICK_CHIPS = [
  { label: 'Estoy estresado', query: 'Algo relajante para desconectarme' },
  { label: 'Noche en familia', query: 'Película familiar para ver con niños' },
  { label: 'Que me haga pensar', query: 'Película profunda y filosófica' },
  { label: 'Solo 90 min', query: 'Película corta de menos de 90 minutos' },
]

export interface HeroMovie {
  title: string
  posterUrl?: string | null
  genreName?: string | null
  genres?: string[]
  director?: string | null
  runtime?: number | null
  compatibilityScore?: number
  explanation?: string
}

export interface HeroSectionProps {
  featuredMovie?: HeroMovie | null
  isLoading?: boolean
  isFavorite?: boolean
  onToggleFavorite?: () => void
  onViewDetails?: () => void
  className?: string
}

export function HeroSection({
  featuredMovie,
  isLoading = false,
  isFavorite = false,
  onToggleFavorite,
  onViewDetails,
  className,
}: HeroSectionProps) {
  const router = useRouter()
  const [prompt, setPrompt] = useState('')

  const handlePromptSubmit = () => {
    if (!prompt.trim()) return
    router.push(`/chat?q=${encodeURIComponent(prompt.trim())}`)
  }

  const handleChipClick = (query: string) => {
    router.push(`/chat?q=${encodeURIComponent(query)}`)
  }

  const genre = featuredMovie?.genres?.[0] ?? featuredMovie?.genreName
  const runtime = featuredMovie?.runtime
    ? `${Math.floor(featuredMovie.runtime / 60)}h ${featuredMovie.runtime % 60}m`
    : null

  const posterUrl = featuredMovie?.posterUrl?.startsWith('/')
    ? `https://image.tmdb.org/t/p/w500${featuredMovie.posterUrl}`
    : featuredMovie?.posterUrl

  return (
    <section
      className={cn(
        'min-h-screen flex items-center',
        'px-6 md:px-12 lg:px-20 py-16',
        className
      )}
    >
      <div className="w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-12 lg:gap-20 items-center">

        {/* ── Left column ─────────────────────────────── */}
        <div className="flex flex-col gap-8 animate-fade-in">

          {/* Live indicator badge */}
          <div className="flex items-center gap-2 w-fit px-3 py-1.5 rounded-full bg-teal/10 border border-teal/30">
            <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse-dot" />
            <span className="text-xs font-medium text-teal tracking-wide">
              Recomendación del momento
            </span>
          </div>

          {/* H1 */}
          <div className="flex flex-col">
            <h1 className="font-display text-6xl lg:text-7xl leading-none text-text">
              Tu película
            </h1>
            <h1 className="font-display text-6xl lg:text-7xl leading-none text-accent">
              de esta
            </h1>
            <h1 className="font-display text-6xl lg:text-7xl leading-none text-accent">
              noche
            </h1>
          </div>

          {/* Subtitle */}
          <p className="text-sm text-muted max-w-md leading-relaxed">
            El grafo de conocimiento analiza tu contexto emocional, social y temporal
            para encontrar exactamente lo que necesitas ver ahora.
          </p>

          {/* SearchPrompt */}
          <div className="flex flex-col gap-3 max-w-md">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-accent text-base select-none">
                  ✦
                </span>
                <Input
                  variant="chat"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
                  placeholder="O cuéntame qué quieres ver hoy…"
                  className="pl-8"
                />
              </div>
              <Button
                variant="primary"
                onClick={handlePromptSubmit}
                disabled={!prompt.trim()}
              >
                <Sparkles className="w-4 h-4 mr-1.5" />
                Recomiéndame
              </Button>
            </div>

            {/* Quick chips */}
            <div className="flex flex-wrap gap-2">
              {QUICK_CHIPS.map(({ label, query }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => handleChipClick(query)}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-xs font-medium',
                    'bg-surface2 text-muted border border-border',
                    'hover:border-teal/40 hover:text-text transition-all duration-200',
                    'hover:scale-[1.03]'
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

        </div>

        {/* ── Right column — RecCard ───────────────────── */}
        <div className="animate-slide-up">
          {isLoading ? (
            <RecCardSkeleton />
          ) : featuredMovie ? (
            <RecCard
              movie={featuredMovie}
              posterUrl={posterUrl ?? null}
              genre={genre ?? null}
              runtime={runtime}
              isFavorite={isFavorite}
              onToggleFavorite={onToggleFavorite}
              onViewDetails={onViewDetails}
            />
          ) : null}
        </div>

      </div>
    </section>
  )
}

// ── RecCard ──────────────────────────────────────────────────────────────────

interface RecCardProps {
  movie: HeroMovie
  posterUrl: string | null
  genre: string | null
  runtime: string | null
  isFavorite: boolean
  onToggleFavorite?: () => void
  onViewDetails?: () => void
}

function RecCard({ movie, posterUrl, genre, runtime, isFavorite, onToggleFavorite, onViewDetails }: RecCardProps) {
  const [imgError, setImgError] = useState(false)
  const hasPoster = Boolean(posterUrl && !imgError)

  return (
    <div className="rounded-2xl overflow-hidden bg-surface border border-border2 shadow-2xl">

      {/* Poster */}
      <div className="relative aspect-[2/3] bg-surface2">
        {hasPoster ? (
          <Image
            src={posterUrl as string}
            alt={`Póster de ${movie.title}`}
            fill
            sizes="400px"
            className="object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <Film className="w-16 h-16 text-muted/20" />
          </div>
        )}

        {/* Live label overlay */}
        <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-bg/80 backdrop-blur-sm border border-teal/40">
          <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse-dot" />
          <span className="text-[11px] font-medium text-teal">Elegida para ti · Esta noche</span>
        </div>
      </div>

      {/* Info */}
      <div className="p-4 flex flex-col gap-3">
        <h2 className="font-display text-2xl text-text leading-tight">{movie.title}</h2>

        <div className="flex items-center gap-2 text-xs text-muted flex-wrap">
          {genre && <span>{genre}</span>}
          {movie.director && <><span>·</span><span>{movie.director}</span></>}
          {runtime && <><span>·</span><span>{runtime}</span></>}
        </div>

        {typeof movie.compatibilityScore === 'number' && (
          <ScoreBar
            score={movie.compatibilityScore}
            label="Compatibilidad semántica"
            animated
            variant="gradient"
          />
        )}

        {movie.explanation && (
          <WhyCard explanation={movie.explanation} />
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <Button variant="primary" className="flex-1" onClick={onViewDetails}>
            <ExternalLink className="w-4 h-4 mr-1.5" />
            Ver detalles
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleFavorite}
            aria-label={isFavorite ? 'Quitar de favoritos' : 'Agregar a favoritos'}
          >
            <Heart className={cn('w-4 h-4', isFavorite ? 'fill-accent text-accent' : '')} />
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

function RecCardSkeleton() {
  return (
    <div className="rounded-2xl overflow-hidden bg-surface border border-border2">
      <SkeletonPoster />
      <div className="p-4 flex flex-col gap-3">
        <SkeletonBox className="h-7 w-3/4" />
        <SkeletonBox className="h-3 w-1/2" />
        <SkeletonBox className="h-2 w-full" />
        <SkeletonBox className="h-16 w-full rounded-lg" />
        <SkeletonBox className="h-10 w-full rounded-md" />
      </div>
    </div>
  )
}
