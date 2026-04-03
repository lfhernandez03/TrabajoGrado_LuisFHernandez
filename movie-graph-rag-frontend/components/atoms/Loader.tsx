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

/** Skeleton de MovieCard completa */
export function SkeletonMovieCard({ className }: SkeletonBaseProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <SkeletonPoster />
      <SkeletonBox className="h-4 w-3/4" />
      <SkeletonBox className="h-3 w-1/2" />
      <SkeletonBox className="h-2 w-full" />
    </div>
  )
}

/** Skeleton de línea de texto */
export function SkeletonText({ className }: SkeletonBaseProps) {
  return (
    <div className={cn('bg-surface2 animate-pulse rounded h-4 w-full', className)} />
  )
}
