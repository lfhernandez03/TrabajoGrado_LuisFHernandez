import React from 'react'
import { cn } from '@/lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'icon' | 'destructive' | 'default'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', asChild = false, ...props }: ButtonProps, ref: any) => {
    const baseStyles =
      'inline-flex items-center justify-center rounded-md font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent'

    const variants: Record<NonNullable<ButtonProps['variant']>, string> = {
      primary: 'bg-accent2 text-bg hover:bg-accent2/90 active:translate-y-0.5',
      secondary: 'bg-teal text-bg hover:bg-teal/90 active:translate-y-0.5',
      default: 'bg-surface2 text-text border border-border hover:bg-surface hover:border-accent',
      ghost:
        'bg-transparent text-text border border-border hover:bg-surface/50 active:bg-surface',
      outline: 'bg-transparent text-text border border-border hover:border-accent hover:text-accent',
      icon: 'bg-transparent text-text hover:bg-surface/50 rounded-full',
      destructive: 'bg-red-600 text-white hover:bg-red-700 active:translate-y-0.5',
    }

    const sizes: Record<NonNullable<ButtonProps['size']>, string> = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-6 text-base',
      icon: 'h-10 w-10 p-0',
    }

    const combinedClassName = cn(baseStyles, variants[variant], sizes[size], className)

    if (asChild && React.isValidElement((props as any).children)) {
      return React.cloneElement((props as any).children, {
        className: cn((props as any).children.props.className, combinedClassName),
        ref,
      } as any)
    }

    return (
      <button
        className={combinedClassName}
        ref={ref}
        {...(props as any)}
      />
    )
  }
)

Button.displayName = 'Button'

export { Button }
