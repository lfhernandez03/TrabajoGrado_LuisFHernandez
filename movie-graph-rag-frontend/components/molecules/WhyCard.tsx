'use client'

import { MessageCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface WhyCardProps {
  /**
   * Explanation text from backend (e.g., explanation field from RecommendationResponse)
   */
  explanation: string
  /**
   * Optional contextual hints for display
   */
  contextHints?: {
    mood?: string
    companion?: string
    genre?: string
  }
  /**
   * Custom CSS class
   */
  className?: string
}

/**
 * WhyCard - "Por qué el grafo eligió esto" explanation card
 *
 * Displays narrative explanation from the backend about why a movie was recommended.
 * The explanation comes from the LLM-generated response that explains the reasoning
 * based on the graph topology and user context.
 *
 * Used in: HeroSection RecCard, MovieDetailHero, inline recommendations
 *
 * @example
 * ```tsx
 * <WhyCard
 *   explanation="Esta película combina la tensión psicológica que buscas con la cinematografía oscura que disfrutas..."
 *   contextHints={{ mood: 'ansioso', genre: 'thriller' }}
 * />
 * ```
 */
export function WhyCard({
  explanation,
  contextHints,
  className,
}: WhyCardProps) {
  return (
    <div
      className={cn(
        'relative',
        'p-4 rounded-lg',
        'bg-surface2/40 border border-border2',
        'backdrop-blur-sm',
        'animate-fade-in',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-2 mb-3">
        {/* Icon */}
        <div className="flex-shrink-0 mt-0.5">
          <div className="w-5 h-5 rounded-full bg-teal/20 flex items-center justify-center">
            <MessageCircle className="w-3 h-3 text-teal" />
          </div>
        </div>

        {/* Title */}
        <h4 className="text-sm font-semibold text-text leading-tight">
          Por qué esta película
        </h4>
      </div>

      {/* Explanation text */}
      <p className="text-sm text-muted leading-relaxed mb-3">
        {explanation}
      </p>

      {/* Context hints (optional) */}
      {contextHints && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-border/50">
          {contextHints.mood && (
            <div className="inline-flex items-center gap-1">
              <span className="text-xs text-muted">Mood:</span>
              <span className="px-1.5 py-0.5 rounded text-xs bg-accent/10 text-accent font-medium">
                {contextHints.mood}
              </span>
            </div>
          )}

          {contextHints.companion && (
            <div className="inline-flex items-center gap-1">
              <span className="text-xs text-muted">Companion:</span>
              <span className="px-1.5 py-0.5 rounded text-xs bg-teal/10 text-teal font-medium">
                {contextHints.companion}
              </span>
            </div>
          )}

          {contextHints.genre && (
            <div className="inline-flex items-center gap-1">
              <span className="text-xs text-muted">Genre:</span>
              <span className="px-1.5 py-0.5 rounded text-xs bg-teal/10 text-teal font-medium">
                {contextHints.genre}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
