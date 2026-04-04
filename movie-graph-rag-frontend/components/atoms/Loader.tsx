'use client'

import { cn } from '@/lib/utils'

// ── Spinner ────────────────────────────────────────────────────────────────

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizeClasses = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }

  return (
    <div
      role="status"
      aria-label="Cargando"
      className={cn(
        'rounded-full border-2 border-border2 border-t-teal animate-spin',
        sizeClasses[size],
        className
      )}
    />
  )
}

// ── Skeleton shapes ────────────────────────────────────────────────────────

interface SkeletonBaseProps {
  className?: string
}

/** Bloque rectangular genérico */
export function SkeletonBox({ className }: SkeletonBaseProps) {
  return (
    <div className={cn('bg-surface2 animate-shimmer rounded-md', className)} />
  )
}

/** Skeleton de póster de película (ratio 2:3) */
export function SkeletonPoster({ className }: SkeletonBaseProps) {
  return (
    <div className={cn('bg-surface2 animate-shimmer rounded-md aspect-2/3 w-full', className)} />
  )
}

/** Skeleton de MovieCard completa (horizontal glassmorphism layout) */
export function SkeletonMovieCard({ className }: SkeletonBaseProps) {
  return (
    <div className={cn(
      'rounded-xl border border-white/10 bg-surface/50 overflow-hidden',
      className
    )}>
      <div className="flex gap-4 min-h-48 p-4">
        {/* Poster thumbnail */}
        <div className="w-28 shrink-0 rounded-lg bg-surface2 animate-shimmer" />

        {/* Content */}
        <div className="flex-1 flex flex-col gap-3 pt-1">
          <div className="flex items-start justify-between gap-3">
            <SkeletonBox className="h-5 w-3/5" />
            <div className="flex gap-1.5 shrink-0">
              <SkeletonBox className="h-7 w-7 rounded-full" />
              <SkeletonBox className="h-7 w-7 rounded-full" />
              <SkeletonBox className="h-7 w-7 rounded-full" />
            </div>
          </div>
          <SkeletonBox className="h-3 w-1/4" />
          <SkeletonBox className="h-3 w-2/5" />
          <SkeletonBox className="h-3 w-full" />
          <SkeletonBox className="h-3 w-full" />
          <SkeletonBox className="h-3 w-4/5" />
        </div>
      </div>
    </div>
  )
}

/** Skeleton de línea de texto */
export function SkeletonText({ className }: SkeletonBaseProps) {
  return (
    <div className={cn('bg-surface2 animate-pulse rounded h-4 w-full', className)} />
  )
}
