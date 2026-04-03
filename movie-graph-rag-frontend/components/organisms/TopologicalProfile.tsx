'use client'

import { TrendingDown, TrendingUp, Minus, Brain, Compass, User } from 'lucide-react'
import { ScoreBar } from '@/components/atoms'
import { Tag } from '@/components/atoms'
import { SkeletonBox, SkeletonText } from '@/components/atoms'
import type { TopologicalProfileResponse } from '@/services/topology.service'
import { cn } from '@/lib/utils'

// ── Types ────────────────────────────────────────────────────────────────────

export interface TopologicalProfileProps {
  profile: TopologicalProfileResponse
  className?: string
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const USER_TYPE_CONFIG = {
  especialista: {
    label: 'Especialista',
    description: 'Te especializas en géneros concretos',
    icon: Brain,
    color: 'text-accent bg-accent/10 border-accent/30',
  },
  equilibrado: {
    label: 'Equilibrado',
    description: 'Balanceas exploración y preferencias',
    icon: User,
    color: 'text-teal bg-teal/10 border-teal/30',
  },
  explorador: {
    label: 'Explorador',
    description: 'Disfrutas la diversidad cinematográfica',
    icon: Compass,
    color: 'text-accent2 bg-accent2/10 border-accent2/30',
  },
}

const TREND_CONFIG = {
  specializing: {
    label: 'Especializándote',
    icon: TrendingDown,
    color: 'text-accent',
    description: 'Tus gustos se están concentrando',
  },
  diversifying: {
    label: 'Diversificando',
    icon: TrendingUp,
    color: 'text-teal',
    description: 'Estás expandiendo tus horizontes',
  },
  stable: {
    label: 'Estable',
    icon: Minus,
    color: 'text-muted',
    description: 'Patrón de consumo consistente',
  },
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

export function TopologicalProfileSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-5', className)}>
      <div className="flex items-center gap-4">
        <SkeletonBox className="h-16 w-16 rounded-xl" />
        <div className="flex-1 space-y-2">
          <SkeletonText className="w-32" />
          <SkeletonText className="w-48" />
        </div>
      </div>
      <SkeletonBox className="h-12 rounded-lg" />
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonBox key={i} className="h-8 rounded" />
        ))}
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function TopologicalProfile({ profile, className }: TopologicalProfileProps) {
  const typeConfig = USER_TYPE_CONFIG[profile.userType]
  const trendConfig = TREND_CONFIG[profile.temporalTrend]
  const TrendIcon = trendConfig.icon
  const TypeIcon = typeConfig.icon

  const clusteredPct =
    profile.totalFavorites > 0
      ? Math.round((profile.clusteredFavorites / profile.totalFavorites) * 100)
      : 0

  return (
    <div className={cn('space-y-6', className)}>

      {/* User type header */}
      <div className="flex items-start gap-4">
        <div className={cn('p-3 rounded-xl border shrink-0', typeConfig.color)}>
          <TypeIcon className="h-6 w-6" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-lg font-bold font-display tracking-wide">
              {typeConfig.label}
            </h3>
            <span className={cn('text-xs px-2 py-0.5 rounded-full border font-medium', typeConfig.color)}>
              {profile.userType}
            </span>
          </div>
          <p className="text-sm text-muted mt-0.5">{typeConfig.description}</p>
        </div>
      </div>

      {/* Exploration index */}
      <div className="bg-surface2 rounded-xl p-4 space-y-3 border border-border">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-muted uppercase tracking-wider">
            Índice de exploración
          </p>
          <span className="text-xs text-muted">Especialista → Explorador</span>
        </div>
        <ScoreBar
          score={profile.explorationIndex}
          label=""
          animated
          variant={profile.explorationIndex > 0.6 ? 'teal' : profile.explorationIndex > 0.3 ? 'gradient' : 'accent'}
        />
        <div className="flex justify-between text-xs text-muted">
          <span>Enfocado</span>
          <span>Diverso</span>
        </div>
      </div>

      {/* Dominant clusters */}
      {profile.dominantClusters.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted uppercase tracking-wider">
            Comunidades dominantes
          </p>
          <div className="space-y-2.5">
            {profile.dominantClusters.slice(0, 5).map((cluster, i) => {
              const pct = Math.round(cluster.weight * 100)
              const isTop = i === 0
              return (
                <div key={cluster.clusterId} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className={cn('truncate', isTop ? 'text-text font-medium' : 'text-muted')}>
                      {isTop && <span className="text-accent mr-1.5">●</span>}
                      {cluster.label}
                    </span>
                    <div className="flex items-center gap-2 shrink-0 ml-2">
                      <span className="text-xs text-muted">{cluster.moviesSeen} vistas</span>
                      <span className={cn('text-xs font-semibold tabular-nums', isTop ? 'text-teal' : 'text-muted')}>
                        {pct}%
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-surface2 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-700',
                        isTop ? 'bg-gradient-to-r from-teal to-accent' : 'bg-border2'
                      )}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Unexplored adjacent */}
      {profile.unexploredAdjacent.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted uppercase tracking-wider">
            Comunidades sin explorar (adyacentes)
          </p>
          <div className="flex flex-wrap gap-2">
            {profile.unexploredAdjacent.map((cluster) => (
              <Tag
                key={cluster.clusterId}
                label={cluster.label}
                variant="static"
              />
            ))}
          </div>
          <p className="text-xs text-muted">
            Estas comunidades están conectadas a tus favoritos pero aún no las has explorado.
          </p>
        </div>
      )}

      {/* Temporal trend */}
      <div className="flex items-center gap-3 p-3 rounded-lg bg-surface2 border border-border">
        <TrendIcon className={cn('h-5 w-5 shrink-0', trendConfig.color)} />
        <div className="min-w-0">
          <p className={cn('text-sm font-medium', trendConfig.color)}>{trendConfig.label}</p>
          <p className="text-xs text-muted mt-0.5 truncate">{profile.trendExplanation}</p>
        </div>
      </div>

      {/* Stats footer */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-surface2 rounded-lg p-3 text-center border border-border">
          <p className="text-2xl font-bold font-display text-text">{profile.totalFavorites}</p>
          <p className="text-xs text-muted mt-0.5">Favoritos totales</p>
        </div>
        <div className="bg-surface2 rounded-lg p-3 text-center border border-border">
          <p className="text-2xl font-bold font-display text-teal">{clusteredPct}%</p>
          <p className="text-xs text-muted mt-0.5">En comunidades</p>
        </div>
      </div>

    </div>
  )
}
