'use client'

import { cn } from '@/lib/utils'


export interface ScoreBarProps {
  /**
   * Score value from 0 to 1
   */
  score: number
  /**
   * Optional label displayed above the bar
   */
  label?: string
  /**
   * Show animated fill effect on mount
   */
  animated?: boolean
  /**
   * Custom CSS class
   */
  className?: string
  /**
   * Color variant: teal (semantic), accent (primary), or gradient
   */
  variant?: 'teal' | 'accent' | 'gradient'
}

/**
 * ScoreBar - Compatibility/semantic score visualization
 *
 * Displays a score from 0-1 with animated fill effect.
 * Commonly used in: RecommendedMovieResponse, MovieCard, HeroSection RecCard
 *
 * @example
 * ```tsx
 * <ScoreBar score={0.91} label="Compatibilidad" animated />
 * ```
 */
export function ScoreBar({
  score,
  label,
  animated = true,
  className,
  variant = 'gradient',
}: ScoreBarProps) {
  // Clamp score to 0-1 range
  const clampedScore = Math.max(0, Math.min(1, score))
  const percentage = Math.round(clampedScore * 100)

  // Determine colors based on variant
  const variantClasses = {
    teal: 'bg-teal',
    accent: 'bg-accent',
    gradient: 'bg-gradient-to-r from-teal to-accent',
  }

  const backgroundColor = variantClasses[variant]

  return (
    <div className={cn('flex flex-col gap-1 animate-slide-up', className)}>
      {/* Label */}
      {label && <p className="text-xs font-medium text-muted">{label}</p>}

      {/* Bar container */}
      <div className="flex items-center gap-2">
        {/* Progress bar */}
        <div
          className="flex-1 h-1.5 bg-surface2 rounded-full overflow-hidden"
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label ?? `Score ${percentage}%`}
        >
          <div
            className={cn(
              'h-full rounded-full',
              backgroundColor,
              animated && 'animate-fill-bar'
            )}
            style={{
              width: `${percentage}%`,
              '--fill-width': `${percentage}%`,
            } as React.CSSProperties}
          />
        </div>

        {/* Score percentage */}
        <span className="text-xs font-semibold text-teal tabular-nums min-w-10 text-right">
          {percentage}%
        </span>
      </div>

    </div>
  )
}
