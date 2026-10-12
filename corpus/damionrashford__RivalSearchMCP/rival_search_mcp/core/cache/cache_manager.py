"""
Advanced caching system for RivalSearchMCP.
Supports Redis and file-based caching with TTL, compression, and performance metrics.
"""

import asyncio
import gzip
import hashlib
import json
import os
import pickle
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from rival_search_mcp.logging.logger import logger


class CacheConfig:
    """Configuration for caching behavior."""

    def __init__(
        self,
        enabled: bool = True,
        backend: str = "file",  # "redis" or "file"
        ttl_seconds: int = 3600,  # 1 hour default
        max_size_mb: int = 100,
        compression: bool = True,
        redis_url: Optional[str] = None,
        redis_db: int = 0,
        file_cache_dir: Optional[str] = None,
    ):
        self.enabled = enabled
        self.backend = backend
        self.ttl_seconds = ttl_seconds
        self.max_size_mb = max_size_mb
        self.compression = compression
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_db = redis_db
        self.file_cache_dir = file_cache_dir or os.path.expanduser("~/.rivalsearch/cache")

        # Create cache directory if using file backend
        if self.backend == "file":
            Path(self.file_cache_dir).mkdir(parents=True, exist_ok=True)


class CacheEntry:
    """Represents a cached item with metadata."""

    def __init__(self, data: Any, ttl_seconds: int):
        self.data = data
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.access_count = 0
        self.last_accessed = self.created_at
        self.size_bytes = len(pickle.dumps(data))

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > self.expires_at

    def access(self) -> Any:
        """Access the cached data and update metadata."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cache entry to dictionary."""
        return {
            "data": self.data,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Deserialize cache entry from dictionary."""
        entry = cls.__new__(cls)
        entry.data = data["data"]
        entry.created_at = data["created_at"]
        entry.expires_at = data["expires_at"]
        entry.access_count = data.get("access_count", 0)
        entry.last_accessed = data.get("last_accessed", data["created_at"])
        entry.size_bytes = data.get("size_bytes", len(pickle.dumps(data["data"])))
        return entry


class BaseCacheBackend:
    """Base class for cache backends."""

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Set a value in cache with TTL."""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        raise NotImplementedError

    async def clear(self) -> bool:
        """Clear all cached values."""
        raise NotImplementedError

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        raise NotImplementedError

    async def cleanup_expired(self) -> int:
        """Clean up expired entries. Returns number of entries removed."""
        raise NotImplementedError


class RedisCacheBackend(BaseCacheBackend):
    """Redis-based cache backend."""

    def __init__(self, config: CacheConfig):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis backend requires redis package: pip install redis")

        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False

    async def _ensure_connection(self):
        """Ensure Redis connection is established."""
        if not self._connected:
            try:
                self.redis_client = redis.Redis.from_url(
                    self.config.redis_url,
                    db=self.config.redis_db,
                    decode_responses=False,  # We'll handle serialization
                )
                await self.redis_client.ping()
                self._connected = True
                logger.info("Connected to Redis cache backend")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
                self._connected = False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis cache."""
        if not self.config.enabled:
            return None

        await self._ensure_connection()
        if not self.redis_client or not self._connected:
            return None

        try:
            data = await self.redis_client.get(key)
            if data is None:
                return None

            # Deserialize
            if self.config.compression:
                data = gzip.decompress(data)

            entry_dict = json.loads(data.decode("utf-8"))
            entry = CacheEntry.from_dict(entry_dict)

            if entry.is_expired():
                await self.delete(key)
                return None

            return entry.access()

        except Exception as e:
            logger.warning(f"Redis cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Set a value in Redis cache."""
        if not self.config.enabled:
            return False

        await self._ensure_connection()
        if not self.redis_client or not self._connected:
            return False

        try:
            entry = CacheEntry(value, ttl_seconds)
            entry_dict = entry.to_dict()

            # Serialize
            data = json.dumps(entry_dict).encode("utf-8")
            if self.config.compression:
                data = gzip.compress(data)

            success = await self.redis_client.setex(key, ttl_seconds, data)
            return bool(success)

        except Exception as e:
            logger.warning(f"Redis cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from Redis cache."""
        if not self.redis_client or not self._connected:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis cache delete error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cached values in Redis."""
        if not self.redis_client or not self._connected:
            return False

        try:
            await self.redis_client.flushdb()
            return True
        except Exception as e:
            logger.warning(f"Redis cache clear error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        if not self.redis_client or not self._connected:
            return {"status": "disconnected"}

        try:
            info = await self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_connections_received": info.get("total_connections_received", 0),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_days": info.get("uptime_in_days", 0),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def cleanup_expired(self) -> int:
        """Redis handles expiration automatically."""
        return 0


class FileCacheBackend(BaseCacheBackend):
    """File-based cache backend."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_dir = Path(config.file_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Create a safe filename from the key
        safe_key = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from file cache."""
        if not self.config.enabled:
            return None

        cache_path = self._get_cache_path(key)

        try:
            if not cache_path.exists():
                self._stats["misses"] += 1
                return None

            # Read and deserialize
            with open(cache_path, "rb") as f:
                if self.config.compression:
                    data = gzip.decompress(f.read())
                else:
                    data = f.read()

            entry_dict = json.loads(data.decode("utf-8"))
            entry = CacheEntry.from_dict(entry_dict)

            if entry.is_expired():
                await self.delete(key)
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return entry.access()

        except Exception as e:
            logger.warning(f"File cache get error for key {key}: {e}")
            self._stats["misses"] += 1
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Set a value in file cache."""
        if not self.config.enabled:
            return False

        cache_path = self._get_cache_path(key)

        try:
            entry = CacheEntry(value, ttl_seconds)
            entry_dict = entry.to_dict()

            # Serialize
            data = json.dumps(entry_dict).encode("utf-8")
            if self.config.compression:
                data = gzip.compress(data)

            # Check size limits
            if len(data) > self.config.max_size_mb * 1024 * 1024:
                logger.warning(f"Cache entry too large for key {key}, skipping")
                return False

            with open(cache_path, "wb") as f:
                f.write(data)

            self._stats["sets"] += 1
            return True

        except Exception as e:
            logger.warning(f"File cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from file cache."""
        cache_path = self._get_cache_path(key)

        try:
            if cache_path.exists():
                cache_path.unlink()
                self._stats["deletes"] += 1
                return True
            return False
        except Exception as e:
            logger.warning(f"File cache delete error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cached values."""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
            return True
        except Exception as e:
            logger.warning(f"File cache clear error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get file cache statistics."""
        try:
            total_files = len(list(self.cache_dir.glob("*.cache")))
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))

            return {
                "status": "active",
                "backend": "file",
                "cache_dir": str(self.cache_dir),
                "total_files": total_files,
                "total_size_mb": total_size / (1024 * 1024),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "deletes": self._stats["deletes"],
                "hit_rate": self._stats["hits"]
                / max(self._stats["hits"] + self._stats["misses"], 1),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def cleanup_expired(self) -> int:
        """Clean up expired cache files."""
        removed_count = 0
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, "rb") as f:
                        if self.config.compression:
                            data = gzip.decompress(f.read())
                        else:
                            data = f.read()

                    entry_dict = json.loads(data.decode("utf-8"))
                    entry = CacheEntry.from_dict(entry_dict)

                    if entry.is_expired():
                        cache_file.unlink()
                        removed_count += 1

                except Exception as e:
                    logger.warning(f"Error checking cache file {cache_file}: {e}")
                    # Remove corrupted files
                    cache_file.unlink()
                    removed_count += 1

        except Exception as e:
            logger.warning(f"Error during cache cleanup: {e}")

        return removed_count


class CacheManager:
    """Main cache manager that handles different backends."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.backend: BaseCacheBackend

        if self.config.backend == "redis":
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available, falling back to file cache")
                self.config.backend = "file"
            else:
                self.backend = RedisCacheBackend(self.config)
        else:
            self.backend = FileCacheBackend(self.config)

        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start periodic cleanup task — no-op if called outside an async context."""
        if not self.config.enabled:
            return
        try:
            self._cleanup_task = asyncio.get_running_loop().create_task(self._periodic_cleanup())
        except RuntimeError:
            pass

    async def _periodic_cleanup(self):
        """Periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                removed = await self.backend.cleanup_expired()
                if removed > 0:
                    logger.info(f"Cleaned up {removed} expired cache entries")
            except Exception as e:
                logger.warning(f"Cache cleanup task error: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self.config.enabled:
            return None

        cache_key = self._make_key(key)
        return await self.backend.get(cache_key)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set a value in cache."""
        if not self.config.enabled:
            return False

        ttl = ttl_seconds or self.config.ttl_seconds
        cache_key = self._make_key(key)
        return await self.backend.set(cache_key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        if not self.config.enabled:
            return False

        cache_key = self._make_key(key)
        return await self.backend.delete(cache_key)

    async def clear(self) -> bool:
        """Clear all cached values."""
        return await self.backend.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = await self.backend.get_stats()
        stats.update(
            {
                "enabled": self.config.enabled,
                "backend": self.config.backend,
                "default_ttl": self.config.ttl_seconds,
                "compression": self.config.compression,
            }
        )
        return stats

    def _make_key(self, key: str) -> str:
        """Create a cache key with namespace."""
        return f"rivalsearch:{key}"

    async def close(self):
        """Clean up resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# Global cache instance
_cache_instance: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
