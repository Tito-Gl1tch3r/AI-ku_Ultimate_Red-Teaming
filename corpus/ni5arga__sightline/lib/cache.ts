interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

const memoryCache = new Map<string, CacheEntry<unknown>>();

const DEFAULT_TTL = 5 * 60 * 1000;
const GEO_TTL = 24 * 60 * 60 * 1000;
const MAX_CACHE_SIZE = 500;

function generateKey(prefix: string, params: Record<string, unknown>): string {
  const sorted = Object.keys(params)
    .sort()
    .map(k => `${k}=${JSON.stringify(params[k])}`)
    .join('&');
  return `${prefix}:${sorted}`;
}

function evictOldest(): void {
  if (memoryCache.size < MAX_CACHE_SIZE) return;
  
  let oldestKey: string | null = null;
  let oldestTime = Infinity;
  
  for (const [key, entry] of memoryCache.entries()) {
    if (entry.timestamp < oldestTime) {
      oldestTime = entry.timestamp;
      oldestKey = key;
    }
  }
  
  if (oldestKey) {
    memoryCache.delete(oldestKey);
  }
}

function cleanExpired(): void {
  const now = Date.now();
  for (const [key, entry] of memoryCache.entries()) {
    if (now - entry.timestamp > entry.ttl) {
      memoryCache.delete(key);
    }
  }
}

export function getCached<T>(key: string): T | null {
  const entry = memoryCache.get(key) as CacheEntry<T> | undefined;
  
  if (!entry) return null;
  
  if (Date.now() - entry.timestamp > entry.ttl) {
    memoryCache.delete(key);
    return null;
  }
  
  return entry.data;
}

export function setCached<T>(key: string, data: T, ttl: number = DEFAULT_TTL): void {
  evictOldest();
  
  memoryCache.set(key, {
    data,
    timestamp: Date.now(),
    ttl
  });
}

export function cacheGeoResult<T>(query: string, data: T): void {
  const key = generateKey('geo', { q: query.toLowerCase().trim() });
  setCached(key, data, GEO_TTL);
}

export function getCachedGeoResult<T>(query: string): T | null {
  const key = generateKey('geo', { q: query.toLowerCase().trim() });
  return getCached<T>(key);
}

export function cacheSearchResult<T>(params: Record<string, unknown>, data: T): void {
  const key = generateKey('search', params);
  setCached(key, data, DEFAULT_TTL);
}

export function getCachedSearchResult<T>(params: Record<string, unknown>): T | null {
  const key = generateKey('search', params);
  return getCached<T>(key);
}

export function clearCache(): void {
  memoryCache.clear();
}

export function getCacheStats(): { size: number; maxSize: number } {
  cleanExpired();
  return {
    size: memoryCache.size,
    maxSize: MAX_CACHE_SIZE
  };
}
