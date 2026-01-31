"""SQLite-based embedding cache."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from memory_service.utils.hashing import embedding_cache_key
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


class EmbeddingCache:
    """SQLite-based cache for embeddings.

    Provides LRU-style caching with TTL support to reduce API calls
    to the embedding service.
    """

    def __init__(
        self,
        cache_path: str = ".cache/embeddings.db",
        max_size: int = 10000,
        ttl_days: int = 30,
    ) -> None:
        """Initialize embedding cache.

        Args:
            cache_path: Path to SQLite database file
            max_size: Maximum number of cached embeddings
            ttl_days: Time-to-live for cache entries in days
        """
        self.cache_path = Path(cache_path)
        self.max_size = max_size
        self.ttl_days = ttl_days
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the cache database."""
        # Ensure directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        async with self._lock:
            self._db = await aiosqlite.connect(str(self.cache_path))

            # Enable WAL mode for better concurrent access
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA synchronous=NORMAL")

            # Create tables
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    cache_key TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    is_fallback BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            """)

            # Create indexes
            await self._db.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_last_accessed
                ON embeddings(last_accessed_at)
            """)
            await self._db.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_created_at
                ON embeddings(created_at)
            """)

            await self._db.commit()
            logger.info("embedding_cache_initialized", path=str(self.cache_path))

    async def get(
        self,
        content: str,
        model: str,
    ) -> tuple[list[float], bool] | None:
        """Retrieve an embedding from the cache.

        Args:
            content: Content that was embedded
            model: Embedding model name

        Returns:
            Tuple of (embedding, is_fallback) or None if not cached
        """
        if not self._db:
            await self.initialize()

        cache_key = embedding_cache_key(content, model)

        async with self._lock:
            try:
                # Check if entry exists and is not expired
                cutoff = datetime.now(timezone.utc) - timedelta(days=self.ttl_days)

                cursor = await self._db.execute(
                    """
                    SELECT embedding, is_fallback FROM embeddings
                    WHERE cache_key = ? AND created_at > ?
                    """,
                    (cache_key, cutoff.isoformat()),
                )
                row = await cursor.fetchone()

                if row:
                    # Update access statistics
                    await self._db.execute(
                        """
                        UPDATE embeddings
                        SET last_accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                        WHERE cache_key = ?
                        """,
                        (cache_key,),
                    )
                    await self._db.commit()

                    # Deserialize embedding using double precision (8 bytes per float)
                    import struct

                    embedding = list(struct.unpack(f"{len(row[0])//8}d", row[0]))
                    is_fallback = bool(row[1])

                    metrics.embedding_cache_hits_total.inc()
                    return (embedding, is_fallback)

                metrics.embedding_cache_misses_total.inc()
                return None

            except Exception as e:
                logger.error("embedding_cache_get_failed", error=str(e))
                metrics.embedding_cache_misses_total.inc()
                return None

    async def set(
        self,
        content: str,
        model: str,
        embedding: list[float],
        is_fallback: bool = False,
    ) -> bool:
        """Store an embedding in the cache.

        Args:
            content: Content that was embedded
            model: Embedding model name
            embedding: Embedding vector
            is_fallback: Whether this is a fallback embedding

        Returns:
            True if stored successfully
        """
        if not self._db:
            await self.initialize()

        cache_key = embedding_cache_key(content, model)
        content_hash = embedding_cache_key(content, "")  # Hash without model

        # Serialize embedding to bytes using double precision (8 bytes per float)
        import struct

        embedding_bytes = struct.pack(f"{len(embedding)}d", *embedding)

        async with self._lock:
            try:
                # Evict old entries if at capacity
                await self._evict_if_needed()

                # Upsert the embedding
                await self._db.execute(
                    """
                    INSERT OR REPLACE INTO embeddings
                    (cache_key, embedding, model, content_hash, is_fallback, created_at, last_accessed_at, access_count)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                    """,
                    (cache_key, embedding_bytes, model, content_hash, is_fallback),
                )
                await self._db.commit()

                logger.debug("embedding_cached", cache_key=cache_key[:16], is_fallback=is_fallback)
                return True

            except Exception as e:
                logger.error("embedding_cache_set_failed", error=str(e))
                return False

    async def get_batch(
        self,
        contents: list[str],
        model: str,
    ) -> dict[str, tuple[list[float], bool] | None]:
        """Retrieve multiple embeddings from cache.

        Args:
            contents: List of content strings
            model: Embedding model name

        Returns:
            Dictionary mapping content to (embedding, is_fallback) or None
        """
        results = {}
        for content in contents:
            results[content] = await self.get(content, model)
        return results

    async def set_batch(
        self,
        embeddings: list[tuple[str, list[float], bool]],
        model: str,
    ) -> int:
        """Store multiple embeddings in cache.

        Args:
            embeddings: List of (content, embedding, is_fallback) tuples
            model: Embedding model name

        Returns:
            Number of embeddings stored
        """
        count = 0
        for content, embedding, is_fallback in embeddings:
            if await self.set(content, model, embedding, is_fallback):
                count += 1
        return count

    async def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is at capacity."""
        cursor = await self._db.execute("SELECT COUNT(*) FROM embeddings")
        row = await cursor.fetchone()
        count = row[0] if row else 0

        if count >= self.max_size:
            # Remove 10% of oldest entries
            to_remove = max(1, self.max_size // 10)
            await self._db.execute(
                """
                DELETE FROM embeddings
                WHERE cache_key IN (
                    SELECT cache_key FROM embeddings
                    ORDER BY last_accessed_at ASC
                    LIMIT ?
                )
                """,
                (to_remove,),
            )
            logger.debug("embedding_cache_evicted", count=to_remove)

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        if not self._db:
            await self.initialize()

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.ttl_days)

        async with self._lock:
            cursor = await self._db.execute(
                "DELETE FROM embeddings WHERE created_at < ?",
                (cutoff.isoformat(),),
            )
            await self._db.commit()

            removed = cursor.rowcount
            if removed > 0:
                logger.info("embedding_cache_cleanup", removed=removed)
            return removed

    async def cleanup_fallback(self) -> int:
        """Remove all fallback embeddings (to be replaced with API embeddings).

        Returns:
            Number of entries removed
        """
        if not self._db:
            await self.initialize()

        async with self._lock:
            cursor = await self._db.execute("DELETE FROM embeddings WHERE is_fallback = TRUE")
            await self._db.commit()

            removed = cursor.rowcount
            if removed > 0:
                logger.info("embedding_cache_fallback_cleanup", removed=removed)
            return removed

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self._db:
            await self.initialize()

        async with self._lock:
            cursor = await self._db.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_fallback THEN 1 ELSE 0 END) as fallback_count,
                    SUM(access_count) as total_accesses,
                    AVG(access_count) as avg_accesses
                FROM embeddings
            """)
            row = await cursor.fetchone()

            return {
                "total_entries": row[0] if row else 0,
                "fallback_entries": row[1] if row else 0,
                "total_accesses": row[2] if row else 0,
                "avg_accesses_per_entry": row[3] if row else 0,
                "max_size": self.max_size,
                "ttl_days": self.ttl_days,
            }

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("embedding_cache_closed")
