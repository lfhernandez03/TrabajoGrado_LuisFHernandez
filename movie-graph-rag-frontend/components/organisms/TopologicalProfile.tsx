'use client'

import { TrendingDown, TrendingUp, Minus, Brain, Compass, User } from 'lucide-react'
import { ScoreBar } from '@/components/atoms'
import { Tag } from '@/components/atoms'
import { SkeletonBox, SkeletonText } from '@/components/atoms'
import type { TopologicalProfileResponse } from '@/services/topology.service'
import { cn } from '@/lib/utils'

// ── Helpers ──────────────────────────────────────────────────────────────────

const USER_TYPE_CONFIG = {
  especialista: {
    label: 'Specialist',
    description: 'You focus on specific genres',
    icon: Brain,
    color: 'text-accent bg-accent/10 border-accent/30',
  },
  equilibrado: {
    label: 'Balanced',
    description: 'You balance exploration and preferences',
    icon: User,
    color: 'text-teal bg-teal/10 border-teal/30',
  },
  explorador: {
    label: 'Explorer',
    description: 'You enjoy cinematic diversity',
    icon: Compass,
    color: 'text-accent2 bg-accent2/10 border-accent2/30',
  },
}

const TREND_CONFIG = {
  specializing: {
    label: 'Specializing',
    icon: TrendingDown,
    color: 'text-accent',
    description: 'Your tastes are narrowing',
  },
  diversifying: {
    label: 'Diversifying',
    icon: TrendingUp,
    color: 'text-teal',
    description: 'You are expanding your horizons',
  },
  stable: {
    label: 'Stable',
    icon: Minus,
    color: 'text-muted',
    description: 'Consistent viewing pattern',
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

// ── Types ────────────────────────────────────────────────────────────────────

export interface TopologicalProfileProps {
  profile: TopologicalProfileResponse
  orientation?: 'vertical' | 'horizontal'
  className?: string
}

// ── Shared sub-sections ───────────────────────────────────────────────────────

function UserTypeHeader({ profile, typeConfig }: { profile: TopologicalProfileResponse; typeConfig: typeof USER_TYPE_CONFIG[keyof typeof USER_TYPE_CONFIG] }) {
  const TypeIcon = typeConfig.icon
  return (
    <div className="flex items-start gap-4">
      <div className={cn('p-3 rounded-xl border shrink-0', typeConfig.color)}>
        <TypeIcon className="h-6 w-6" />
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="text-lg font-bold font-display tracking-wide">{typeConfig.label}</h3>
          <span className={cn('text-xs px-2 py-0.5 rounded-full border font-medium', typeConfig.color)}>
            {profile.userType}
          </span>
        </div>
        <p className="text-sm text-muted mt-0.5">{typeConfig.description}</p>
      </div>
    </div>
  )
}

function ExplorationIndex({ profile }: { profile: TopologicalProfileResponse }) {
  return (
    <div className="bg-surface2 rounded-xl p-4 space-y-3 border border-border">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted uppercase tracking-wider">Exploration index</p>
        <span className="text-xs text-muted">Specialist → Explorer</span>
      </div>
      <ScoreBar
        score={profile.explorationIndex}
        label=""
        animated
        variant={profile.explorationIndex > 0.6 ? 'teal' : profile.explorationIndex > 0.3 ? 'gradient' : 'accent'}
      />
      <div className="flex justify-between text-xs text-muted">
        <span>Focused</span>
        <span>Diverse</span>
      </div>
    </div>
  )
}

function DominantClusters({ profile }: { profile: TopologicalProfileResponse }) {
  if (profile.dominantClusters.length === 0) return null
  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-muted uppercase tracking-wider">Dominant communities</p>
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
                  <span className="text-xs text-muted">{cluster.moviesSeen} seen</span>
                  <span className={cn('text-xs font-semibold tabular-nums', isTop ? 'text-teal' : 'text-muted')}>
                    {pct}%
                  </span>
                </div>
              </div>
              <div className="h-1.5 bg-surface2 rounded-full overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all duration-700', isTop ? 'bg-linear-to-r from-teal to-accent' : 'bg-border2')}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function UnexploredAdjacent({ profile }: { profile: TopologicalProfileResponse }) {
  if (profile.unexploredAdjacent.length === 0) return null
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted uppercase tracking-wider">Unexplored adjacent communities</p>
      <div className="flex flex-wrap gap-2">
        {profile.unexploredAdjacent.map((cluster) => (
          <Tag key={cluster.clusterId} label={cluster.label} variant="static" />
        ))}
      </div>
    </div>
  )
}

function TrendAndStats({ profile, trendConfig, clusteredPct }: {
  profile: TopologicalProfileResponse
  trendConfig: typeof TREND_CONFIG[keyof typeof TREND_CONFIG]
  clusteredPct: number
}) {
  const TrendIcon = trendConfig.icon
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 p-3 rounded-lg bg-surface2 border border-border">
        <TrendIcon className={cn('h-5 w-5 shrink-0', trendConfig.color)} />
        <div className="min-w-0">
          <p className={cn('text-sm font-medium', trendConfig.color)}>{trendConfig.label}</p>
          <p className="text-xs text-muted mt-0.5 truncate">{profile.trendExplanation}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-surface2 rounded-lg p-3 text-center border border-border">
          <p className="text-2xl font-bold font-display text-text">{profile.totalFavorites}</p>
          <p className="text-xs text-muted mt-0.5">Total favorites</p>
        </div>
        <div className="bg-surface2 rounded-lg p-3 text-center border border-border">
          <p className="text-2xl font-bold font-display text-teal">{clusteredPct}%</p>
          <p className="text-xs text-muted mt-0.5">In communities</p>
        </div>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function TopologicalProfile({ profile, orientation = 'vertical', className }: TopologicalProfileProps) {
  const typeConfig = USER_TYPE_CONFIG[profile.userType]
  const trendConfig = TREND_CONFIG[profile.temporalTrend]

  const clusteredPct =
    profile.totalFavorites > 0
      ? Math.round((profile.clusteredFavorites / profile.totalFavorites) * 100)
      : 0

  if (orientation === 'horizontal') {
    return (
      <div className={cn('space-y-5', className)}>
        {/* Row 1: 3 columns */}
        <div className="grid grid-cols-1 md:grid-cols-[220px_1fr_200px] gap-6 items-start">
          {/* Col 1 — User type */}
          <UserTypeHeader profile={profile} typeConfig={typeConfig} />

          {/* Col 2 — Exploration + clusters */}
          <div className="space-y-4">
            <ExplorationIndex profile={profile} />
            <DominantClusters profile={profile} />
          </div>

          {/* Col 3 — Trend + stats */}
          <TrendAndStats profile={profile} trendConfig={trendConfig} clusteredPct={clusteredPct} />
        </div>

        {/* Row 2 — Unexplored (full width, compact) */}
        <UnexploredAdjacent profile={profile} />
      </div>
    )
  }

  // Vertical (sidebar) layout — unchanged behaviour
  return (
    <div className={cn('space-y-6', className)}>
      <UserTypeHeader profile={profile} typeConfig={typeConfig} />
      <ExplorationIndex profile={profile} />
      <DominantClusters profile={profile} />
      <UnexploredAdjacent profile={profile} />
      <TrendAndStats profile={profile} trendConfig={trendConfig} clusteredPct={clusteredPct} />
    </div>
  )
}
