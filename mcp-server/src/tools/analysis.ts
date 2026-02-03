import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { ToolContext } from "../context.js";
import { logger } from "../utils/logger.js";

function toolResult(data: unknown) {
  return {
    content: [{
      type: "text" as const,
      text: JSON.stringify(data, null, 2)
    }]
  };
}

function toolError(code: string, message: string, suggestion?: string) {
  return toolResult({
    error: {
      code,
      message,
      suggestion
    }
  });
}

export function registerAnalysisTools(server: McpServer, ctx: ToolContext): void {
  // check_consistency - Verify code follows stored patterns
  server.tool(
    "check_consistency",
    "Check if code follows established patterns in memory",
    {
      code: z.string().min(1).max(100000),
      component_name: z.string().optional()
    },
    async (input) => {
      try {
        // Find similar code patterns
        const embedding = await ctx.voyage.embed(input.code);

        const patterns = await ctx.qdrant.search({
          collections: [ctx.collectionName("code_pattern"), ctx.collectionName("design")],
          vector: embedding,
          limit: 5,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        const issues: Array<{
          type: string;
          severity: "error" | "warning" | "info";
          message: string;
          related_pattern?: string;
        }> = [];

        // Check if there are any similar patterns
        if (patterns.length === 0) {
          issues.push({
            type: "no_patterns",
            severity: "info",
            message: "No similar patterns found in memory"
          });
        } else {
          // Compare with highest scoring pattern
          const topPattern = patterns[0];
          if (topPattern && topPattern.score < 0.7) {
            issues.push({
              type: "low_similarity",
              severity: "warning",
              message: "Code does not closely match any stored patterns",
              related_pattern: String(topPattern.payload["content"]).substring(0, 200)
            });
          }
        }

        return toolResult({
          consistent: issues.filter(i => i.severity === "error").length === 0,
          issues: issues,
          matched_patterns: patterns.map(p => ({
            memory_id: p.id,
            type: p.payload["type"],
            similarity: p.score,
            preview: String(p.payload["content"]).substring(0, 200)
          }))
        });
      } catch (error) {
        logger.error("check_consistency failed", { error: String(error) });
        return toolError("CONSISTENCY_ERROR", String(error));
      }
    }
  );

  // validate_fix - Validate a fix against design requirements
  server.tool(
    "validate_fix",
    "Validate a proposed fix against stored design and requirements",
    {
      fix_description: z.string().min(1).max(10000),
      code_changes: z.string().optional(),
      requirement_ids: z.array(z.string().uuid()).optional()
    },
    async (input) => {
      try {
        // Search for related requirements and design
        const embedding = await ctx.voyage.embed(input.fix_description);

        const requirements = await ctx.qdrant.search({
          collections: [ctx.collectionName("requirements")],
          vector: embedding,
          limit: 5,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        const designs = await ctx.qdrant.search({
          collections: [ctx.collectionName("design")],
          vector: embedding,
          limit: 3,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        const validationResults = {
          requirements_alignment: requirements.length > 0 && (requirements[0]?.score || 0) > 0.5,
          design_alignment: designs.length > 0 && (designs[0]?.score || 0) > 0.5,
          related_requirements: requirements.map(r => ({
            memory_id: r.id,
            content_preview: String(r.payload["content"]).substring(0, 300),
            alignment_score: r.score
          })),
          related_designs: designs.map(d => ({
            memory_id: d.id,
            content_preview: String(d.payload["content"]).substring(0, 300),
            alignment_score: d.score
          }))
        };

        return toolResult({
          valid: validationResults.requirements_alignment || validationResults.design_alignment,
          ...validationResults
        });
      } catch (error) {
        logger.error("validate_fix failed", { error: String(error) });
        return toolError("VALIDATION_ERROR", String(error));
      }
    }
  );

  // get_design_context - Get ADRs and patterns for a component
  server.tool(
    "get_design_context",
    "Retrieve design decisions, ADRs, and patterns for a component",
    {
      component_name: z.string().min(1).max(200),
      include_related: z.boolean().default(true)
    },
    async (input) => {
      try {
        const embedding = await ctx.voyage.embed(input.component_name);

        // Search design documents
        const designs = await ctx.qdrant.search({
          collections: [ctx.collectionName("design")],
          vector: embedding,
          limit: 10,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        // Search code patterns
        const patterns = await ctx.qdrant.search({
          collections: [ctx.collectionName("code_pattern")],
          vector: embedding,
          limit: 5,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        // Get graph relationships if requested
        let relatedComponents: Record<string, unknown>[] = [];
        if (input.include_related) {
          try {
            // Search for component nodes
            const componentResults = await ctx.neo4j.query(
              `MATCH (c:Component {project_id: $projectId})
               WHERE c.name CONTAINS $name OR c.memory_id IN $designIds
               RETURN c LIMIT 1`,
              {
                name: input.component_name,
                designIds: designs.slice(0, 3).map(d => d.id)
              }
            );

            if (componentResults.length > 0) {
              const componentNode = componentResults[0] as { c: { memory_id: string } };
              relatedComponents = await ctx.neo4j.getRelated(
                componentNode.c.memory_id,
                undefined,
                2
              );
            }
          } catch {
            // Graph not available
          }
        }

        return toolResult({
          component: input.component_name,
          designs: designs.map(d => ({
            memory_id: d.id,
            content: d.payload["content"],
            metadata: d.payload["metadata"],
            relevance: d.score
          })),
          patterns: patterns.map(p => ({
            memory_id: p.id,
            content: p.payload["content"],
            metadata: p.payload["metadata"],
            relevance: p.score
          })),
          related_components: relatedComponents
        });
      } catch (error) {
        logger.error("get_design_context failed", { error: String(error) });
        return toolError("CONTEXT_ERROR", String(error));
      }
    }
  );

  // trace_requirements - Trace requirements to implementations
  server.tool(
    "trace_requirements",
    "Trace requirements to their implementations in code",
    {
      requirement_id: z.string().uuid().optional(),
      requirement_text: z.string().optional()
    },
    async (input) => {
      try {
        if (!input.requirement_id && !input.requirement_text) {
          return toolError(
            "INVALID_INPUT",
            "Either requirement_id or requirement_text must be provided"
          );
        }

        let requirementContent: string;
        let requirementId: string | undefined = input.requirement_id;

        if (input.requirement_id) {
          // Fetch the requirement
          const point = await ctx.qdrant.get(
            ctx.collectionName("requirements"),
            input.requirement_id
          );

          if (!point) {
            return toolError("NOT_FOUND", "Requirement not found");
          }

          requirementContent = String(point.payload["content"]);
        } else {
          requirementContent = input.requirement_text!;
        }

        // Search for related code
        const embedding = await ctx.voyage.embed(requirementContent);

        const implementations = await ctx.qdrant.search({
          collections: [
            ctx.collectionName("code_pattern"),
            ctx.collectionName("function"),
            ctx.collectionName("component")
          ],
          vector: embedding,
          limit: 10,
          filter: {
            must: [
              { key: "project_id", match: { value: ctx.projectId } },
              { key: "deleted", match: { value: false } }
            ]
          }
        });

        // Try graph tracing if we have an ID
        let graphTrace: Record<string, unknown>[] = [];
        if (requirementId) {
          try {
            graphTrace = await ctx.neo4j.getRelated(
              requirementId,
              ["IMPLEMENTS", "SATISFIES", "TESTS"],
              3
            );
          } catch {
            // Graph not available
          }
        }

        return toolResult({
          requirement: {
            id: requirementId,
            content_preview: requirementContent.substring(0, 500)
          },
          implementations: implementations.map(i => ({
            memory_id: i.id,
            type: i.payload["type"],
            content_preview: String(i.payload["content"]).substring(0, 300),
            metadata: i.payload["metadata"],
            relevance: i.score
          })),
          graph_trace: graphTrace
        });
      } catch (error) {
        logger.error("trace_requirements failed", { error: String(error) });
        return toolError("TRACE_ERROR", String(error));
      }
    }
  );

  logger.info("Registered 4 analysis tools");
}
