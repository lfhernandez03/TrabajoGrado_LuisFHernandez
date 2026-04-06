import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Get a CSS variable value from the document
 * @param varName - Variable name without '--' prefix
 * @returns The CSS variable value or undefined if not found
 */
export function getCSSVariable(varName: string): string | undefined {
  if (typeof window === "undefined") return undefined
  const value = getComputedStyle(document.documentElement).getPropertyValue(
    `--${varName}`.trim()
  )
  return value ? value.trim() : undefined
}

/**
 * Set a CSS variable value
 * @param varName - Variable name without '--' prefix
 * @param value - The value to set
 */
export function setCSSVariable(varName: string, value: string): void {
  if (typeof window === "undefined") return
  document.documentElement.style.setProperty(`--${varName}`, value)
}

/**
 * CineGraph color tokens for easy access
 */
export const COLORS = {
  bg: "var(--bg)",
  surface: "var(--surface)",
  surface2: "var(--surface2)",
  text: "var(--text)",
  muted: "var(--muted)",
  accent: "var(--accent)",
  accent2: "var(--accent2)",
  teal: "var(--teal)",
  purple: "var(--color-purple)",
  border: "var(--border)",
  border2: "var(--border2)",
} as const
