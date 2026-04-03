'use client'

import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ContextChip {
  id: string
  label: string
  icon?: string
  type?: 'mood' | 'companion' | 'energy' | 'runtime' | 'genre'
}

export interface ContextChipsProps {
  /**
   * Array of context chips to display
   */
  chips: ContextChip[]
  /**
   * Callback when a chip is removed
   */
  onRemove?: (chipId: string) => void
  /**
   * Allow removing chips
   */
  removable?: boolean
  /**
   * Custom CSS class
   */
  className?: string
}

/**
 * ContextChips - Removable context filter indicators
 *
 * Displays accumulated context from chat conversations or user preferences.
 * Each chip can have an optional icon and is removable.
 *
 * Used in: ChatModule panel, SearchPrompt context display
 *
 * @example
 * ```tsx
 * <ContextChips
 *   chips={[
 *     { id: '1', label: 'Estresado', type: 'mood', icon: '😰' },
 *     { id: '2', label: '90 min', type: 'runtime' }
 *   ]}
 *   onRemove={(id) => removeContext(id)}
 */
export function ContextChips({
  chips,
  onRemove,
  removable = true,
  className,
}: ContextChipsProps) {
  if (chips.length === 0) {
    return null
  }

  const getChipColor = (type?: string) => {
    switch (type) {
      case 'mood':
        return 'bg-accent/10 text-accent border-accent/30'
      case 'companion':
        return 'bg-teal/10 text-teal border-teal/30'
      case 'energy':
        return 'bg-accent2/10 text-accent2 border-accent2/30'
      case 'runtime':
        return 'bg-muted/10 text-muted border-muted/30'
      case 'genre':
        return 'bg-teal/10 text-teal border-teal/30'
      default:
        return 'bg-surface2 text-text border-border'
    }
  }

  return (
    <div
      className={cn(
        'flex flex-wrap gap-2',
        'animate-slide-up',
        className
      )}
    >
      {chips.map((chip) => (
        <div
          key={chip.id}
          className={cn(
            'inline-flex items-center gap-1.5',
            'px-2.5 py-1 rounded-full',
            'border text-xs font-medium',
            'transition-all duration-200',
            'hover:transform hover:scale-105',
            getChipColor(chip.type)
          )}
        >
          {/* Optional icon */}
          {chip.icon && (
            <span className="text-sm leading-none">{chip.icon}</span>
          )}

          {/* Label */}
          <span className="leading-none">{chip.label}</span>

          {/* Remove button */}
          {removable && onRemove && (
            <button
              onClick={() => onRemove(chip.id)}
              className={cn(
                'ml-0.5 p-0.5 rounded hover:bg-white/20',
                'transition-colors duration-150',
                'focus-visible:outline-offset-0'
              )}
              aria-label={`Remove ${chip.label}`}
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
