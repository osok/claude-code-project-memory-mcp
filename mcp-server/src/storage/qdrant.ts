import { QdrantClient } from "@qdrant/js-client-rest";
import { logger } from "../utils/logger.js";
import type { Point, SearchParams, SearchResult } from "../types/index.js";
import type { MemoryType, MEMORY_TYPES } from "../types/memory.js";

const VECTOR_SIZE = 1024; // voyage-code-3 dimensions

export class QdrantAdapter {
  private client: QdrantClient;
  private projectId: string;

  constructor(url: string, projectId: string) {
    this.client = new QdrantClient({ url });
    this.projectId = projectId;
  }

  collectionName(memoryType: string): string {
    return `${this.projectId}_${memoryType}`;
  }

  allCollections(): string[] {
    const types: readonly MemoryType[] = [
      "requirements", "design", "architecture", "code_pattern", "component",
      "function", "test_result", "test_history", "session", "user_preference"
    ];
    return types.map(t => this.collectionName(t));
  }

  async ensureCollection(memoryType: string): Promise<void> {
    const name = this.collectionName(memoryType);
    try {
      const exists = await this.client.collectionExists(name);

      if (!exists.exists) {
        await this.client.createCollection(name, {
          vectors: {
            size: VECTOR_SIZE,
            distance: "Cosine"
          }
        });
        logger.info("Created collection", { name });
      }
    } catch (error) {
      logger.error("Failed to ensure collection", { name, error: String(error) });
      throw error;
    }
  }

  async ensureAllCollections(): Promise<void> {
    const types: readonly string[] = [
      "requirements", "design", "architecture", "code_pattern", "component",
      "function", "test_result", "test_history", "session", "user_preference"
    ];
    for (const type of types) {
      await this.ensureCollection(type);
    }
  }

  async upsert(collection: string, point: Point): Promise<void> {
    await this.client.upsert(collection, {
      wait: true,
      points: [{
        id: point.id,
        vector: point.vector,
        payload: point.payload
      }]
    });
  }

  async upsertBatch(collection: string, points: Point[]): Promise<void> {
    await this.client.upsert(collection, {
      wait: true,
      points: points.map(p => ({
        id: p.id,
        vector: p.vector,
        payload: p.payload
      }))
    });
  }

  async search(params: SearchParams): Promise<SearchResult[]> {
    const results: SearchResult[] = [];

    for (const collection of params.collections) {
      try {
        const searchResult = await this.client.search(collection, {
          vector: params.vector,
          limit: params.limit,
          filter: params.filter ? {
            must: params.filter.must?.map(m => ({
              key: m.key,
              match: { value: m.match.value }
            }))
          } : undefined,
          with_payload: true
        });

        for (const hit of searchResult) {
          results.push({
            id: String(hit.id),
            score: hit.score,
            payload: (hit.payload || {}) as Record<string, unknown>
          });
        }
      } catch (error) {
        // Collection might not exist yet
        logger.debug("Search failed for collection", { collection, error: String(error) });
      }
    }

    // Sort by score descending and limit
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, params.limit);
  }

  // Simple similarity search with a vector in a single collection
  async searchSimilar(
    collection: string,
    vector: number[],
    limit: number = 5,
    scoreThreshold: number = 0.7
  ): Promise<Array<{ id: string; score: number }>> {
    try {
      const searchResult = await this.client.search(collection, {
        vector,
        limit,
        score_threshold: scoreThreshold,
        filter: {
          must: [
            { key: "project_id", match: { value: this.projectId } },
            { key: "deleted", match: { value: false } }
          ]
        },
        with_payload: false
      });

      return searchResult.map(hit => ({
        id: String(hit.id),
        score: hit.score
      }));
    } catch {
      // Collection may not exist
      return [];
    }
  }

  async get(collection: string, id: string): Promise<Point | null> {
    try {
      const result = await this.client.retrieve(collection, {
        ids: [id],
        with_payload: true,
        with_vector: true
      });

      if (result.length === 0) {
        return null;
      }

      const point = result[0];
      if (!point) {
        return null;
      }

      // Validate project_id matches
      const payload = point.payload as Record<string, unknown> | null | undefined;
      if (payload?.["project_id"] !== this.projectId) {
        return null;
      }

      return {
        id: String(point.id),
        vector: point.vector as number[],
        payload: payload || {}
      };
    } catch (error) {
      logger.error("Failed to get point", { collection, id, error: String(error) });
      return null;
    }
  }

  async softDelete(collection: string, id: string): Promise<boolean> {
    try {
      // Get current point
      const point = await this.get(collection, id);
      if (!point) {
        return false;
      }

      // Update deleted flag
      await this.client.setPayload(collection, {
        wait: true,
        points: [id],
        payload: {
          deleted: true,
          updated_at: new Date().toISOString()
        }
      });

      return true;
    } catch (error) {
      logger.error("Failed to soft delete", { collection, id, error: String(error) });
      return false;
    }
  }

  async getStatistics(): Promise<{ collections: Array<{ name: string; count: number }> }> {
    const stats: { collections: Array<{ name: string; count: number }> } = { collections: [] };

    for (const collection of this.allCollections()) {
      try {
        const info = await this.client.getCollection(collection);
        stats.collections.push({
          name: collection,
          count: info.points_count || 0
        });
      } catch {
        // Collection doesn't exist
      }
    }

    return stats;
  }
}
