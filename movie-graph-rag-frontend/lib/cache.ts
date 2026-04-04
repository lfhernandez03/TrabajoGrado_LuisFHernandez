/**
 * In-memory TTL cache for expensive API calls.
 * Lives for the duration of the browser session (survives SPA navigation,
 * resets on hard refresh). No external dependencies required.
 */

interface CacheEntry<T> {
  data: T
  expiresAt: number
}

class TtlCache {
  private store = new Map<string, CacheEntry<unknown>>()

  get<T>(key: string): T | null {
    const entry = this.store.get(key) as CacheEntry<T> | undefined
    if (!entry) return null
    if (Date.now() > entry.expiresAt) {
      this.store.delete(key)
      return null
    }
    return entry.data
  }

  set<T>(key: string, data: T, ttlMs: number): void {
    this.store.set(key, { data, expiresAt: Date.now() + ttlMs })
  }

  invalidate(key: string): void {
    this.store.delete(key)
  }

  clear(): void {
    this.store.clear()
  }
}

export const pageCache = new TtlCache()

/**
 * Wrap a fetcher with the cache. If a fresh entry exists it is returned
 * immediately; otherwise the fetcher runs, caches its result, and returns it.
 *
 * @param key    Unique cache key (include all params that affect the result).
 * @param ttlMs  How long the entry stays valid in milliseconds.
 * @param fetcher  Async function that performs the actual API call.
 */
export async function withCache<T>(
  key: string,
  ttlMs: number,
  fetcher: () => Promise<T>,
): Promise<T> {
  const hit = pageCache.get<T>(key)
  if (hit !== null) return hit
  const result = await fetcher()
  pageCache.set(key, result, ttlMs)
  return result
}

// Convenience TTL constants (milliseconds)
export const TTL = {
  SHORT: 5 * 60 * 1000,   //  5 min — user-specific data
  MED:  15 * 60 * 1000,   // 15 min — graph queries
  LONG: 30 * 60 * 1000,   // 30 min — stable catalogue data
} as const
