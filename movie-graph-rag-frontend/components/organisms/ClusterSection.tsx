'use client'

import Image from 'next/image'
import Link from 'next/link'
import { Layers, Star, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/atoms'
import { Tag } from '@/components/atoms'
import { SkeletonBox, SkeletonText } from '@/components/atoms'
import type { MovieClusterResponse, ClusterMovie } from '@/services/clusters.service'
import { cn } from '@/lib/utils'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ClusterSectionProps {
  data: MovieClusterResponse
  className?: string
}

// ── Poster mini-card ──────────────────────────────────────────────────────────

function ClusterMovieMini({ movie }: { movie: ClusterMovie }) {
  return (
    <div className="flex items-center gap-3 py-2 group">
      {/* Poster */}
      <div className="relative w-9 h-13 rounded overflow-hidden shrink-0 bg-surface2">
        {movie.posterUrl ? (
          <Image
            src={movie.posterUrl}
            alt={movie.title}
            fill
            className="object-cover"
            sizes="36px"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <Layers className="h-3 w-3 text-muted" />
          </div>
        )}
      </div>
      {/* Info */}
      <div className="min-w-0 flex-1">
        <p className="text-sm truncate text-text group-hover:text-accent transition-colors">
          {movie.title}
        </p>
        <div className="flex items-center gap-1.5 mt-0.5">
          {movie.genre && (
            <span className="text-xs text-muted truncate">{movie.genre}</span>
          )}
          {movie.rating != null && (
            <span className="flex items-center gap-0.5 text-xs text-muted shrink-0">
              <Star className="h-2.5 w-2.5 fill-accent text-accent" />
              {movie.rating.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

export function ClusterSectionSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-5', className)}>
      <SkeletonBox className="h-20 rounded-xl" />
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-3 items-center py-1">
            <SkeletonBox className="w-9 h-13 rounded" />
            <div className="flex-1 space-y-1.5">
              <SkeletonText className="w-3/4" />
              <SkeletonText className="w-1/3" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function ClusterSection({ data, className }: ClusterSectionProps) {
  const { cluster, intraCluster, adjacentClusters } = data

  return (
    <div className={cn('space-y-6', className)}>

      {/* Cluster header card */}
      <div className="rounded-xl bg-surface2 border border-border p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Layers className="h-4 w-4 text-teal shrink-0" />
              <span className="text-xs font-medium text-muted uppercase tracking-wider">
                Comunidad
              </span>
            </div>
            <h3 className="font-display text-xl tracking-wide text-text">{cluster.label}</h3>
          </div>
          <Badge variant="teal" size="md" className="shrink-0">
            {cluster.size} películas
          </Badge>
        </div>

        {/* Dominant genres */}
        {cluster.dominantGenres.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {cluster.dominantGenres.map((genre) => (
              <Tag key={genre} label={genre} variant="static" />
            ))}
          </div>
        )}
      </div>

      {/* Intra-cluster movies */}
      {intraCluster.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted uppercase tracking-wider mb-3">
            Películas de la misma comunidad
          </p>
          <div className="divide-y divide-border">
            {intraCluster.slice(0, 8).map((movie) => (
              <ClusterMovieMini key={movie.title} movie={movie} />
            ))}
          </div>
        </div>
      )}

      {/* Adjacent clusters */}
      {adjacentClusters.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted uppercase tracking-wider">
            Comunidades adyacentes
          </p>
          <div className="space-y-3">
            {adjacentClusters.slice(0, 3).map((adj) => (
              <div
                key={adj.clusterId}
                className="rounded-lg border border-border bg-surface2 p-3 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-text truncate">{adj.label}</p>
                  <ArrowRight className="h-3.5 w-3.5 text-muted shrink-0" />
                </div>

                {/* Shared genres */}
                {adj.sharedGenres.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {adj.sharedGenres.slice(0, 3).map((g) => (
                      <Tag key={g} label={g} variant="static" />
                    ))}
                  </div>
                )}

                {/* Bridge movies */}
                {adj.bridgeMovies.length > 0 && (
                  <div className="space-y-0">
                    {adj.bridgeMovies.slice(0, 2).map((m) => (
                      <ClusterMovieMini key={m.title} movie={m} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
