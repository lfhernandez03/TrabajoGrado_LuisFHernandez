'use client'

import { TrendingDown, TrendingUp, Minus, Brain, Compass, User, Sparkles } from 'lucide-react'
import { SkeletonBox, SkeletonText } from '@/components/atoms'
import type { TopologicalProfileResponse } from '@/services/topology.service'
import { cn } from '@/lib/utils'

// ── Config ────────────────────────────────────────────────────────────────────

const USER_TYPE_CONFIG = {
  specialist: {
    label: 'Specialist',
    description: 'You focus on specific genres',
    icon: Brain,
    color: 'text-accent bg-accent/10 border-accent/30',
  },
  balanced: {
    label: 'Balanced',
    description: 'You balance exploration and preferences',
    icon: User,
    color: 'text-teal bg-teal/10 border-teal/30',
  },
  explorer: {
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
    bg: 'bg-accent/10',
  },
  diversifying: {
    label: 'Diversifying',
    icon: TrendingUp,
    color: 'text-teal',
    bg: 'bg-teal/10',
  },
  stable: {
    label: 'Stable',
    icon: Minus,
    color: 'text-muted',
    bg: 'bg-muted/10',
  },
}

// Rank 0 → richest, rank 4 → faintest
const CLUSTER_BAR_COLORS = [
  'bg-gradient-to-r from-teal to-accent',
  'bg-teal/55',
  'bg-teal/30',
  'bg-border2',
  'bg-border2/50',
]

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

// ── Sub-sections ──────────────────────────────────────────────────────────────

function UserTypeHeader({
  profile,
  typeConfig,
}: {
  profile: TopologicalProfileResponse
  typeConfig: (typeof USER_TYPE_CONFIG)[keyof typeof USER_TYPE_CONFIG]
}) {
  const TypeIcon = typeConfig.icon
  return (
    <div className="flex items-start gap-3">
      <div className={cn('p-3 rounded-xl border shrink-0', typeConfig.color)}>
        <TypeIcon className="h-6 w-6" />
      </div>
      <div className="min-w-0">
        <h3 className="text-lg font-bold font-display tracking-wide leading-tight">{typeConfig.label}</h3>
        <span className={cn('text-[11px] px-2 py-0.5 rounded-full border font-medium inline-block mt-1', typeConfig.color)}>
          {profile.userType}
        </span>
        <p className="text-xs text-muted mt-1.5 leading-snug">{typeConfig.description}</p>
      </div>
    </div>
  )
}

function ExplorationIndex({ profile }: { profile: TopologicalProfileResponse }) {
  const pct = Math.round(profile.explorationIndex * 100)
  const barClass =
    profile.explorationIndex > 0.6
      ? 'bg-gradient-to-r from-teal to-accent'
      : profile.explorationIndex > 0.3
        ? 'bg-gradient-to-r from-teal/70 to-teal'
        : 'bg-accent'

  return (
    <div className="bg-surface2 rounded-xl p-4 space-y-2.5 border border-border">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold text-muted uppercase tracking-widest">Exploration index</p>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-muted/70">Specialist → Explorer</span>
          <span className="text-sm font-bold text-teal tabular-nums">{pct}%</span>
        </div>
      </div>

      {/* Bar with position-marker dot */}
      <div className="relative h-3 flex items-center">
        <div className="absolute inset-x-0 h-2 bg-bg rounded-full overflow-hidden border border-border/50">
          <div
            className={cn('h-full rounded-full animate-fill-bar', barClass)}
            style={
              { width: `${pct}%`, '--fill-width': `${pct}%` } as React.CSSProperties
            }
          />
        </div>
        <div
          className="absolute w-3 h-3 bg-text rounded-full border-2 border-bg shadow-lg z-10 transition-all duration-700"
          style={{ left: `calc(${pct}% - 6px)` }}
        />
      </div>

      <div className="flex justify-between text-[11px] text-muted/70">
        <span>Focused</span>
        <span>Diverse</span>
      </div>
    </div>
  )
}

function DominantClusters({ profile }: { profile: TopologicalProfileResponse }) {
  if (profile.dominantClusters.length === 0) return null
  const clusters = profile.dominantClusters.slice(0, 5)

  return (
    <div className="space-y-3">
      <p className="text-[11px] font-semibold text-muted uppercase tracking-widest">Dominant communities</p>
      <div className="space-y-3">
        {clusters.map((cluster, i) => {
          const pct = Math.round(cluster.weight * 100)
          const isTop = i === 0
          const barColor = CLUSTER_BAR_COLORS[i] ?? 'bg-border2/40'

          return (
            <div key={cluster.clusterId} className="space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={cn('text-[10px] font-bold tabular-nums shrink-0 w-4', isTop ? 'text-accent' : 'text-muted/40')}>
                    {i + 1}
                  </span>
                  <span className={cn('truncate text-xs', isTop ? 'text-text font-semibold' : 'text-text/75')}>
                    {cluster.label}
                  </span>
                </div>
                <div className="flex items-center gap-2.5 shrink-0 ml-2">
                  <span className="text-[11px] text-muted">{cluster.moviesSeen} seen</span>
                  <span className={cn('text-xs font-bold tabular-nums min-w-8 text-right', isTop ? 'text-teal' : 'text-muted/70')}>
                    {pct}%
                  </span>
                </div>
              </div>
              <div className="h-1.5 bg-bg rounded-full overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all duration-700', barColor)}
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
    <div className="space-y-2.5">
      <p className="text-[11px] font-semibold text-muted uppercase tracking-widest">
        Unexplored adjacent communities
      </p>
      <div className="flex flex-wrap gap-1.5">
        {profile.unexploredAdjacent.map((cluster) => (
          <span
            key={cluster.clusterId}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-teal/5 border border-teal/20 text-teal/70 hover:bg-teal/10 hover:text-teal hover:border-teal/40 transition-all duration-200 cursor-default"
          >
            <Sparkles className="h-3 w-3 opacity-70 shrink-0" />
            {cluster.label}
          </span>
        ))}
      </div>
    </div>
  )
}

function TrendAndStats({
  profile,
  trendConfig,
  clusteredPct,
}: {
  profile: TopologicalProfileResponse
  trendConfig: (typeof TREND_CONFIG)[keyof typeof TREND_CONFIG]
  clusteredPct: number
}) {
  const TrendIcon = trendConfig.icon
  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3 p-3 rounded-xl bg-surface2 border border-border">
        <div className={cn('p-1.5 rounded-lg shrink-0 mt-0.5', trendConfig.bg)}>
          <TrendIcon className={cn('h-4 w-4', trendConfig.color)} />
        </div>
        <div className="min-w-0">
          <p className={cn('text-sm font-semibold', trendConfig.color)}>{trendConfig.label}</p>
          <p className="text-[11px] text-muted mt-1 leading-relaxed">{profile.trendExplanation}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <div className="bg-surface2 rounded-xl p-3.5 text-center border border-border">
          <p className="text-2xl font-bold font-display text-text leading-none">{profile.totalFavorites}</p>
          <p className="text-[11px] text-muted mt-1.5 leading-tight">
            Total
            <br />
            favorites
          </p>
        </div>
        <div className="bg-surface2 rounded-xl p-3.5 text-center border border-border">
          <p className="text-2xl font-bold font-display text-teal leading-none">{clusteredPct}%</p>
          <p className="text-[11px] text-muted mt-1.5 leading-tight">
            In
            <br />
            communities
          </p>
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
        <div className="grid grid-cols-1 md:grid-cols-[190px_1fr_210px] gap-6 items-start">
          <UserTypeHeader profile={profile} typeConfig={typeConfig} />
          <div className="space-y-4">
            <ExplorationIndex profile={profile} />
            <DominantClusters profile={profile} />
          </div>
          <TrendAndStats profile={profile} trendConfig={trendConfig} clusteredPct={clusteredPct} />
        </div>
        <UnexploredAdjacent profile={profile} />
      </div>
    )
  }

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
