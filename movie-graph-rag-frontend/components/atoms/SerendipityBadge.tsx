'use client'

import { cn } from '@/lib/utils'


export interface SerendipityBadgeProps {
  /**
   * Serendipity score (0-1)
   * Badge only shows when score > 0.6
   */
  score: number
  /**
   * Position of badge on card
   */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
  /**
   * Custom CSS class
   */
  className?: string
}

/**
 * SerendipityBadge - Visual indicator for "surprise" movies
 *
 * Shows a serendipity badge when score > 0.6 (indicating a bridge movie
 * that connects different clusters in the knowledge graph).
 *
 * Displays on: MovieCard hover, RecommendationCarousel items
 *
 * @example
 * ```tsx
 * {serendipityScore > 0.6 && <SerendipityBadge score={serendipityScore} />}
 * ```
 */
export function SerendipityBadge({
  score,
  position = 'top-right',
  className,
}: SerendipityBadgeProps) {
  // Only show if score > 0.6
  if (score <= 0.6) {
    return null
  }

  const positionClasses = {
    'top-right': 'top-2 right-2',
    'top-left': 'top-2 left-2',
    'bottom-right': 'bottom-2 right-2',
    'bottom-left': 'bottom-2 left-2',
  }

  return (
    <div
      className={cn(
        'absolute z-10',
        positionClasses[position],
        'flex items-center gap-1',
        'px-2 py-1 rounded-full',
        'bg-teal/20 border border-teal/50 backdrop-blur-sm',
        'animate-fade-in',
        className
      )}
    >
      {/* Sparkle icon */}
      <span className="text-teal text-sm">✨</span>

      {/* Label */}
      <span className="text-xs font-medium text-teal whitespace-nowrap">
        Serendipity
      </span>

      {/* Score dot */}
      <div
        className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse-dot"
        aria-hidden="true"
      />
    </div>
  )
}
