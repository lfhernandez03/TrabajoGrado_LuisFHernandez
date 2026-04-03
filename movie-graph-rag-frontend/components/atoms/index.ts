// ── Atoms ─────────────────────────────────────────────────────────────────────
// Primitive, indivisible UI building blocks per Atomic Design

// UI primitives (from @/components/ui)
export { Button, type ButtonProps } from '@/components/ui/button'
export { Badge, type BadgeProps } from '@/components/ui/badge'
export { Input, type InputProps } from '@/components/ui/input'

// Custom atoms
export { Tag, type TagProps } from './Tag'
export { ScoreBar, type ScoreBarProps } from './ScoreBar'
export { SerendipityBadge, type SerendipityBadgeProps } from './SerendipityBadge'
export {
  Spinner,
  SkeletonBox,
  SkeletonPoster,
  SkeletonMovieCard,
  SkeletonText,
  type SpinnerProps,
} from './Loader'
