"""Voyage AI embedding client."""

import asyncio
import time
from typing import Any

import httpx

from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_CODE_3_DIMENSIONS = 1024
MAX_BATCH_SIZE = 128
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1.0


class VoyageClient:
    """Client for Voyage AI embedding API.

    Provides methods for:
    - Single text embedding
    - Batch embedding with rate limit handling
    - Automatic retry with exponential backoff
    """

    def __init__(
        self,
        api_key: Any,
        model: str = "voyage-code-3",
        timeout: float = 30.0,
    ) -> None:
        """Initialize Voyage client.

        Args:
            api_key: Voyage AI API key
            model: Embedding model name
            timeout: Request timeout in seconds
        """
        # Extract secret value if SecretStr
        self.api_key = api_key.get_secret_value() if hasattr(api_key, "get_secret_value") else api_key
        self.model = model
        self.timeout = timeout

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        logger.info("voyage_client_initialized", model=model)

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            1024-dimensional embedding vector
        """
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(
        self,
        texts: list[str],
        input_type: str = "document",
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            input_type: Input type hint ("document" or "query")

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        start_time = time.perf_counter()

        # Process in batches
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i : i + MAX_BATCH_SIZE]
            batch_embeddings = await self._embed_batch_with_retry(batch, input_type)
            all_embeddings.extend(batch_embeddings)

        duration = time.perf_counter() - start_time
        metrics.record_embedding(
            source="voyage",
            status="success",
            duration=duration,
            batch_size=len(texts),
        )

        logger.debug(
            "voyage_batch_complete",
            count=len(texts),
            duration_ms=int(duration * 1000),
        )

        return all_embeddings

    async def _embed_batch_with_retry(
        self,
        texts: list[str],
        input_type: str,
    ) -> list[list[float]]:
        """Embed a batch with retry logic.

        Args:
            texts: List of texts (max MAX_BATCH_SIZE)
            input_type: Input type hint

        Returns:
            List of embedding vectors
        """
        last_error: Exception | None = None
        retry_delay = BASE_RETRY_DELAY

        for attempt in range(MAX_RETRIES):
            try:
                return await self._embed_batch_request(texts, input_type)

            except httpx.HTTPStatusError as e:
                last_error = e

                if e.response.status_code == 429:
                    # Rate limited - check Retry-After header
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        retry_delay = float(retry_after)
                    else:
                        retry_delay = retry_delay * 2

                    logger.warning(
                        "voyage_rate_limited",
                        attempt=attempt + 1,
                        retry_after=retry_delay,
                    )
                    await asyncio.sleep(retry_delay)

                elif e.response.status_code >= 500:
                    # Server error - retry with backoff
                    logger.warning(
                        "voyage_server_error",
                        status=e.response.status_code,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

                else:
                    # Client error - don't retry
                    logger.error(
                        "voyage_client_error",
                        status=e.response.status_code,
                        body=e.response.text,
                    )
                    raise

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                logger.warning(
                    "voyage_connection_error",
                    error=str(e),
                    attempt=attempt + 1,
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

        # All retries exhausted
        metrics.record_embedding(
            source="voyage",
            status="error",
            duration=0,
            batch_size=len(texts),
        )

        if last_error:
            raise last_error

        raise RuntimeError("Embedding failed after retries")

    async def _embed_batch_request(
        self,
        texts: list[str],
        input_type: str,
    ) -> list[list[float]]:
        """Make a single batch embedding request.

        Args:
            texts: List of texts
            input_type: Input type hint

        Returns:
            List of embedding vectors
        """
        response = await self._client.post(
            VOYAGE_API_URL,
            json={
                "model": self.model,
                "input": texts,
                "input_type": input_type,
            },
        )
        response.raise_for_status()

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]

        # Validate dimensions
        for emb in embeddings:
            if len(emb) != VOYAGE_CODE_3_DIMENSIONS:
                raise ValueError(
                    f"Expected {VOYAGE_CODE_3_DIMENSIONS} dimensions, got {len(emb)}"
                )

        return embeddings

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
        logger.info("voyage_client_closed")
