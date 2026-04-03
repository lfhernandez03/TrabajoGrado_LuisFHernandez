import React from 'react'
import { cn } from '@/lib/utils'

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'teal' | 'accent' | 'secondary' | 'destructive' | 'outline'
  size?: 'sm' | 'md' | 'lg'
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    const variants = {
      default: 'bg-surface text-text border border-border',
      teal: 'bg-teal/10 text-teal border border-teal/30',
      accent: 'bg-accent/10 text-accent border border-accent/30',
      secondary: 'bg-surface2 text-text border border-border2',
      destructive: 'bg-red-600/10 text-red-400 border border-red-600/30',
      outline: 'bg-transparent text-text border border-border',
    }

    const sizes = {
      sm: 'px-2 py-1 text-xs',
      md: 'px-2.5 py-1.5 text-sm',
      lg: 'px-3 py-2 text-base',
    }

    return (
      <div
        className={cn(
          'inline-flex items-center rounded-full font-medium',
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)

Badge.displayName = 'Badge'

export { Badge }
