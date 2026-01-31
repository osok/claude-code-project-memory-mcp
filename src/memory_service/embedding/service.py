"""Main embedding service with caching and fallback support."""

import asyncio
import time
from typing import Any

from memory_service.embedding.voyage_client import VoyageClient
from memory_service.storage.cache import EmbeddingCache
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


class EmbeddingService:
    """Embedding service with cache-first retrieval and optional fallback.

    Provides:
    - Cache-first embedding retrieval
    - Batch embedding with cache separation
    - Optional local fallback model
    - Automatic cache population
    """

    def __init__(
        self,
        api_key: Any,
        model: str = "voyage-code-3",
        cache_path: str = ".cache/embeddings.db",
        cache_size: int = 10000,
        cache_ttl_days: int = 30,
        fallback_enabled: bool = False,
        fallback_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        """Initialize embedding service.

        Args:
            api_key: Voyage AI API key
            model: Voyage embedding model name
            cache_path: Path to SQLite cache file
            cache_size: Maximum cache entries
            cache_ttl_days: Cache TTL in days
            fallback_enabled: Whether to use local fallback
            fallback_model: HuggingFace model for fallback
        """
        self.model = model
        self.fallback_enabled = fallback_enabled
        self.fallback_model_name = fallback_model

        # Initialize Voyage client
        self._voyage_client = VoyageClient(api_key=api_key, model=model)

        # Initialize cache
        self._cache = EmbeddingCache(
            cache_path=cache_path,
            max_size=cache_size,
            ttl_days=cache_ttl_days,
        )

        # Fallback model (lazy loaded)
        self._fallback: Any | None = None

        logger.info(
            "embedding_service_initialized",
            model=model,
            fallback_enabled=fallback_enabled,
        )

    async def initialize(self) -> None:
        """Initialize the embedding service."""
        await self._cache.initialize()

    async def embed(
        self,
        text: str,
        use_cache: bool = True,
        input_type: str = "document",
    ) -> tuple[list[float], bool]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed
            use_cache: Whether to use cache
            input_type: Input type hint ("document" or "query")

        Returns:
            Tuple of (embedding, is_fallback)
        """
        start = time.perf_counter()

        # Check cache first
        if use_cache:
            cached = await self._cache.get(text, self.model)
            if cached:
                duration = time.perf_counter() - start
                metrics.record_embedding(
                    source="cache",
                    status="success",
                    duration=duration,
                )
                return cached

        # Generate new embedding
        try:
            embedding = await self._voyage_client.embed(text)

            # Cache the result
            if use_cache:
                await self._cache.set(text, self.model, embedding, is_fallback=False)

            return (embedding, False)

        except Exception as e:
            logger.error("voyage_embed_failed", error=str(e))

            # Try fallback if enabled
            if self.fallback_enabled:
                embedding = await self._embed_fallback(text)

                # Cache as fallback
                if use_cache:
                    await self._cache.set(text, self.model, embedding, is_fallback=True)

                return (embedding, True)

            raise

    async def embed_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
        input_type: str = "document",
    ) -> list[tuple[list[float], bool]]:
        """Generate embeddings for multiple texts.

        Separates cached and uncached texts for efficient API usage.

        Args:
            texts: List of texts to embed
            use_cache: Whether to use cache
            input_type: Input type hint

        Returns:
            List of (embedding, is_fallback) tuples
        """
        if not texts:
            return []

        results: list[tuple[list[float], bool] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # Check cache for each text
        if use_cache:
            for i, text in enumerate(texts):
                cached = await self._cache.get(text, self.model)
                if cached:
                    results[i] = cached
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                new_embeddings = await self._voyage_client.embed_batch(
                    uncached_texts,
                    input_type=input_type,
                )

                # Cache and assign results
                for idx, (text, embedding) in zip(uncached_indices, zip(uncached_texts, new_embeddings)):
                    if use_cache:
                        await self._cache.set(text, self.model, embedding, is_fallback=False)
                    results[idx] = (embedding, False)

            except Exception as e:
                logger.error("voyage_batch_embed_failed", error=str(e))

                # Try fallback for failed texts
                if self.fallback_enabled:
                    for idx, text in zip(uncached_indices, uncached_texts):
                        if results[idx] is None:
                            embedding = await self._embed_fallback(text)
                            if use_cache:
                                await self._cache.set(text, self.model, embedding, is_fallback=True)
                            results[idx] = (embedding, True)
                else:
                    raise

        # Ensure all results are populated
        final_results: list[tuple[list[float], bool]] = []
        for result in results:
            if result is None:
                raise RuntimeError("Embedding generation failed for some texts")
            final_results.append(result)

        return final_results

    async def embed_for_query(self, text: str) -> list[float]:
        """Generate embedding optimized for query/search.

        Args:
            text: Query text

        Returns:
            Embedding vector
        """
        # For queries, skip cache to get fresh embeddings
        embedding, _ = await self.embed(text, use_cache=False, input_type="query")
        return embedding

    async def _embed_fallback(self, text: str) -> list[float]:
        """Generate embedding using local fallback model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (padded/truncated to 1024 dimensions)
        """
        start = time.perf_counter()

        if self._fallback is None:
            await self._load_fallback_model()

        try:
            # Generate embedding with fallback model
            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self._fallback.encode(text).tolist(),  # type: ignore
            )

            # Pad or truncate to 1024 dimensions
            if len(embedding) < 1024:
                embedding = embedding + [0.0] * (1024 - len(embedding))
            elif len(embedding) > 1024:
                embedding = embedding[:1024]

            duration = time.perf_counter() - start
            metrics.record_embedding(
                source="fallback",
                status="success",
                duration=duration,
            )

            return embedding

        except Exception as e:
            metrics.record_embedding(
                source="fallback",
                status="error",
                duration=0,
            )
            logger.error("fallback_embed_failed", error=str(e))
            raise

    async def _load_fallback_model(self) -> None:
        """Load the fallback embedding model."""
        logger.info("loading_fallback_model", model=self.fallback_model_name)

        loop = asyncio.get_running_loop()

        def load_model():
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(self.fallback_model_name)

        self._fallback = await loop.run_in_executor(None, load_model)
        logger.info("fallback_model_loaded")

    async def refresh_fallback_embeddings(self) -> int:
        """Refresh all fallback embeddings with API embeddings.

        Returns:
            Number of embeddings refreshed
        """
        # This would iterate through cache entries marked as fallback
        # and regenerate them using the API
        # For now, just clear fallback cache entries
        return await self._cache.cleanup_fallback()

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        return await self._cache.get_stats()

    async def close(self) -> None:
        """Close the embedding service."""
        await self._voyage_client.close()
        await self._cache.close()
        logger.info("embedding_service_closed")
