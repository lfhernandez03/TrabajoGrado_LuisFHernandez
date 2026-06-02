import { useRef, useCallback } from 'react'

/**
 * Returns a `run(key, fn)` helper that ensures only one call per key is
 * in-flight at a time. Subsequent calls with the same key are silently
 * dropped until the first one resolves or rejects.
 *
 * Useful for toggle buttons (e.g. add/remove favorite) where rapid clicks
 * would otherwise fire duplicate API requests.
 */
export function usePendingSet() {
  const pending = useRef(new Set<string>())

  const run = useCallback(async (key: string, fn: () => Promise<void>) => {
    if (pending.current.has(key)) return
    pending.current.add(key)
    try {
      await fn()
    } finally {
      pending.current.delete(key)
    }
  }, [])

  return run
}
