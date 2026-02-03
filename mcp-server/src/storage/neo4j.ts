import neo4j, { Driver, Session } from "neo4j-driver";
import { logger } from "../utils/logger.js";

export class Neo4jAdapter {
  private driver: Driver;
  private projectId: string;

  constructor(uri: string, user: string, password: string, projectId: string) {
    this.driver = neo4j.driver(uri, neo4j.auth.basic(user, password));
    this.projectId = projectId;
  }

  async verifyConnectivity(): Promise<void> {
    await this.driver.verifyConnectivity();
    logger.info("Neo4j connection verified");
  }

  async createNode(
    label: string,
    memoryId: string,
    properties: Record<string, unknown>
  ): Promise<void> {
    const session = this.driver.session();
    try {
      await session.run(
        `CREATE (n:${label} $props)`,
        {
          props: {
            memory_id: memoryId,
            project_id: this.projectId,
            created_at: new Date().toISOString(),
            ...properties
          }
        }
      );
    } finally {
      await session.close();
    }
  }

  async updateNode(
    memoryId: string,
    properties: Record<string, unknown>
  ): Promise<boolean> {
    const session = this.driver.session();
    try {
      const result = await session.run(
        `MATCH (n {memory_id: $memoryId, project_id: $projectId})
         SET n += $props, n.updated_at = datetime()
         RETURN n`,
        {
          memoryId,
          projectId: this.projectId,
          props: properties
        }
      );
      return result.records.length > 0;
    } finally {
      await session.close();
    }
  }

  async deleteNode(memoryId: string): Promise<boolean> {
    const session = this.driver.session();
    try {
      const result = await session.run(
        `MATCH (n {memory_id: $memoryId, project_id: $projectId})
         SET n.deleted = true, n.updated_at = datetime()
         RETURN n`,
        {
          memoryId,
          projectId: this.projectId
        }
      );
      return result.records.length > 0;
    } finally {
      await session.close();
    }
  }

  async createRelationship(
    sourceId: string,
    relationshipType: string,
    targetId: string,
    properties?: Record<string, unknown>
  ): Promise<void> {
    const session = this.driver.session();
    try {
      await session.run(
        `MATCH (a {memory_id: $sourceId, project_id: $projectId})
         MATCH (b {memory_id: $targetId, project_id: $projectId})
         CREATE (a)-[r:${relationshipType} $props]->(b)`,
        {
          sourceId,
          targetId,
          projectId: this.projectId,
          props: properties || {}
        }
      );
    } finally {
      await session.close();
    }
  }

  async query(
    cypher: string,
    params: Record<string, unknown> = {}
  ): Promise<Record<string, unknown>[]> {
    // Security: Only allow read queries
    const normalizedQuery = cypher.trim().toLowerCase();
    if (!normalizedQuery.startsWith("match") && !normalizedQuery.startsWith("optional match")) {
      throw new Error("Only MATCH queries are allowed for security");
    }

    // Check for write operations
    const writeOperations = ["create", "delete", "remove", "set", "merge", "detach"];
    for (const op of writeOperations) {
      if (normalizedQuery.includes(op)) {
        throw new Error(`Write operation '${op}' is not allowed in read-only queries`);
      }
    }

    const session = this.driver.session({ defaultAccessMode: neo4j.session.READ });
    try {
      const result = await session.run(cypher, {
        ...params,
        projectId: this.projectId
      });
      return result.records.map(r => r.toObject());
    } finally {
      await session.close();
    }
  }

  async getRelated(
    entityId: string,
    relationshipTypes: string[] | undefined,
    depth: number = 1
  ): Promise<Record<string, unknown>[]> {
    const session = this.driver.session({ defaultAccessMode: neo4j.session.READ });
    try {
      let relPattern = "";
      if (relationshipTypes && relationshipTypes.length > 0) {
        relPattern = `:${relationshipTypes.join("|")}`;
      }

      const result = await session.run(
        `MATCH (start {memory_id: $entityId, project_id: $projectId})
         MATCH path = (start)-[${relPattern}*1..${depth}]-(related)
         WHERE related.project_id = $projectId AND (related.deleted IS NULL OR related.deleted = false)
         RETURN DISTINCT related, length(path) as distance
         ORDER BY distance
         LIMIT 50`,
        {
          entityId,
          projectId: this.projectId
        }
      );

      return result.records.map(r => ({
        ...r.get("related").properties,
        distance: r.get("distance").toNumber()
      }));
    } finally {
      await session.close();
    }
  }

  async getStatistics(): Promise<{ nodeCount: number; relationshipCount: number }> {
    const session = this.driver.session({ defaultAccessMode: neo4j.session.READ });
    try {
      const nodeResult = await session.run(
        `MATCH (n {project_id: $projectId}) WHERE n.deleted IS NULL OR n.deleted = false RETURN count(n) as count`,
        { projectId: this.projectId }
      );

      const relResult = await session.run(
        `MATCH (a {project_id: $projectId})-[r]->(b {project_id: $projectId}) RETURN count(r) as count`,
        { projectId: this.projectId }
      );

      return {
        nodeCount: nodeResult.records[0]?.get("count").toNumber() || 0,
        relationshipCount: relResult.records[0]?.get("count").toNumber() || 0
      };
    } finally {
      await session.close();
    }
  }

  async close(): Promise<void> {
    await this.driver.close();
    logger.info("Neo4j connection closed");
  }
}
