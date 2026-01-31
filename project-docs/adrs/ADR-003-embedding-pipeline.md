# ADR-003: Embedding Pipeline Architecture

## Status

Accepted

## Context

The memory system relies on Voyage-Code-3 embeddings for semantic search and duplicate detection. Embedding generation is:
- Relatively expensive (API call to Voyage AI)
- Subject to rate limits
- Critical path for memory operations

Requirements addressed:
- REQ-MEM-FN-030: Compute embeddings using Voyage-Code-3
- REQ-MEM-INT-080: Voyage AI API integration
- REQ-MEM-INT-081: Batch embedding requests (max 128)
- REQ-MEM-INT-082: Local caching of embeddings
- REQ-MEM-INT-083: Rate limit handling
- REQ-MEM-INT-084: Fallback to local model
- REQ-MEM-PERF-004: 100 embeddings/second for cached content

## Options Considered

### Option 1: Synchronous Embedding on Demand

- **Pros**:
  - Simple implementation
  - No background processing
  - Immediate consistency
- **Cons**:
  - High latency for uncached content
  - Rate limits block operations
  - No batching benefits

### Option 2: Asynchronous Queue with Background Worker

- **Pros**:
  - Non-blocking memory operations
  - Efficient batching
  - Graceful rate limit handling
- **Cons**:
  - Eventual consistency (memory not immediately searchable)
  - More complex architecture
  - Need to track pending embeddings

### Option 3: Hybrid (Cache-First with Async Fallback)

- **Pros**:
  - Immediate response for cached content
  - Background processing for cache misses
  - Batching for bulk operations
  - Graceful degradation
- **Cons**:
  - More complex state management
  - Need to handle "embedding pending" state

## Decision

**Option 3: Hybrid Pipeline** - Synchronous cache lookup with async batched generation for misses.

### Pipeline Architecture

```
Input Text
    |
    v
[Content Hash Computation]
    |
    v
[Cache Lookup (LRU + Disk)]
    |
    +-- Hit --> Return Embedding
    |
    +-- Miss --> [Batch Queue]
                     |
                     v
                [Batch Processor]
                (when batch full OR timeout)
                     |
                     v
                [Voyage AI API]
                     |
                     v
                [Cache Store]
                     |
                     v
                [Update Qdrant]
```

### Components

1. **Content Hasher**
   - SHA-256 hash of content for cache key
   - Handles text normalization (whitespace, encoding)

2. **Embedding Cache**
   - Two-tier: In-memory LRU (configurable size, default 10,000) + SQLite disk cache
   - Key: content hash
   - Value: embedding vector + timestamp
   - Eviction: LRU for memory, TTL for disk (30 days)

3. **Batch Queue**
   - In-memory queue for pending embedding requests
   - Max batch size: 128 (Voyage API limit)
   - Flush trigger: batch full OR 100ms timeout OR explicit flush
   - Returns Future/Promise for callers to await

4. **Batch Processor**
   - Single worker thread consuming batch queue
   - Rate limiter: exponential backoff on 429 responses
   - Retry logic: 3 attempts with backoff

5. **Fallback Handler**
   - Triggered when Voyage AI unavailable after retries
   - Uses local model (sentence-transformers/all-MiniLM-L6-v2 default)
   - Flags embeddings as `local_fallback=true`
   - Queues for re-embedding when Voyage available

### API Interaction

```python
# Synchronous (blocking) - for single embedding needs
embedding = await embedding_service.get_embedding(text)

# Batch (non-blocking) - for bulk indexing
futures = embedding_service.batch_embed(texts)
embeddings = await asyncio.gather(*futures)

# Preload cache - for bulk operations
await embedding_service.preload(texts)
```

### Cache Storage Schema (SQLite)

```sql
CREATE TABLE embedding_cache (
    content_hash TEXT PRIMARY KEY,
    embedding BLOB,
    model TEXT,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP,
    is_fallback BOOLEAN
);

CREATE INDEX idx_cache_accessed ON embedding_cache(last_accessed);
```

## Consequences

### Positive
- Fast response for repeated content (cache hit)
- Efficient API usage through batching
- Graceful handling of rate limits
- System remains functional during Voyage outages
- Bulk indexing benefits from batching

### Negative
- Memory not immediately searchable if embedding pending
- Local fallback embeddings may have different quality
- Cache invalidation needed if model changes

### Risks
- **Risk**: Cache grows unbounded
- **Mitigation**: LRU eviction for memory, TTL eviction for disk, configurable limits

- **Risk**: Voyage AI API changes
- **Mitigation**: Abstract behind interface, version-pin client library

- **Risk**: Fallback embeddings incompatible with Voyage embeddings
- **Mitigation**: Track `is_fallback` flag, re-embed when Voyage available, keep separate Qdrant collection for fallback if needed

## Requirements Addressed

- REQ-MEM-FN-030 (Voyage-Code-3 embeddings)
- REQ-MEM-INT-080 through REQ-MEM-INT-084 (Voyage integration)
- REQ-MEM-PERF-004 (embedding throughput)
- REQ-MEM-REL-003 (graceful unavailability handling)

## References

- Voyage AI Documentation
- SQLite for caching: https://www.sqlite.org/
- Python asyncio patterns for batching
