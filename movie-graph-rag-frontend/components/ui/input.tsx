import React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'search' | 'chat'
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant = 'default', type = 'text', ...props }, ref) => {
    const variants = {
      default:
        'bg-surface2 text-text border border-border placeholder:text-muted focus:border-accent focus:bg-surface2/80',
      search:
        'bg-surface2 text-text border border-border placeholder:text-muted focus:border-teal focus:ring-1 focus:ring-teal/20',
      chat: 'bg-surface2 text-text border border-border placeholder:text-muted focus:border-accent2 focus:ring-1 focus:ring-accent2/20',
    }

    return (
      <input
        type={type}
        className={cn(
          'w-full px-4 py-2.5 rounded-md',
          'transition-all duration-200',
          'outline-none',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variants[variant],
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)

Input.displayName = 'Input'

export { Input }
