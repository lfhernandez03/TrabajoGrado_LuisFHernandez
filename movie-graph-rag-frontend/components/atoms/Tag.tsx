'use client'

import { cn } from '@/lib/utils'

export interface TagProps {
  label: string
  /** static = display only, selectable = toggleable */
  variant?: 'static' | 'selectable'
  selected?: boolean
  onToggle?: (label: string) => void
  size?: 'sm' | 'md'
  className?: string
}

export function Tag({
  label,
  variant = 'static',
  selected = false,
  onToggle,
  size = 'md',
  className,
}: TagProps) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px]',
    md: 'px-2.5 py-1 text-xs',
  }

  const baseClasses = cn(
    'inline-flex items-center rounded-full border font-medium transition-all duration-200',
    sizeClasses[size]
  )

  if (variant === 'selectable') {
    return (
      <button
        type="button"
        onClick={() => onToggle?.(label)}
        className={cn(
          baseClasses,
          selected
            ? 'bg-teal/15 text-teal border-teal/50 hover:bg-teal/25'
            : 'bg-surface2 text-muted border-border hover:border-teal/40 hover:text-text',
          'cursor-pointer',
          className
        )}
        aria-pressed={selected}
      >
        {selected && <span className="mr-1 text-teal">●</span>}
        {label}
      </button>
    )
  }

  return (
    <span
      className={cn(
        baseClasses,
        'bg-surface2 text-muted border-border',
        className
      )}
    >
      {label}
    </span>
  )
}
