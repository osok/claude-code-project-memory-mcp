/**
 * Re-index project documentation and code
 *
 * Run with: npx tsx scripts/reindex-project.ts
 */
import { randomUUID } from 'node:crypto';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative, extname } from 'node:path';
import { QdrantAdapter } from '../mcp-server/src/storage/qdrant.js';
import { Neo4jAdapter } from '../mcp-server/src/storage/neo4j.js';
import { VoyageClient } from '../mcp-server/src/embedding/voyage.js';
import { loadConfig } from '../mcp-server/src/config.js';

const PROJECT_ID = 'claude-memory-mcp';
const PROJECT_ROOT = '/ai/work/claude-code/claude-code-project-memory-mcp';

// Document type detection
function detectDocType(filePath: string): string {
  const lowerPath = filePath.toLowerCase();

  if (lowerPath.includes('requirement') || lowerPath.includes('req-') ||
      lowerPath.includes('/requirements/') || lowerPath.includes('requirement-docs')) {
    return 'requirements';
  }

  if (lowerPath.includes('adr') || lowerPath.includes('architecture') ||
      lowerPath.includes('decision') || lowerPath.includes('/adrs/')) {
    return 'architecture';
  }

  if (lowerPath.includes('design') || lowerPath.includes('spec') ||
      lowerPath.includes('/design-docs/') || lowerPath.includes('/designs/')) {
    return 'design';
  }

  return 'design';
}

// Extract title from markdown
function extractTitle(content: string, filePath: string): string {
  const titleMatch = content.match(/^#\s+(.+)$/m);
  if (titleMatch && titleMatch[1]) {
    return titleMatch[1].trim();
  }
  const basename = filePath.split('/').pop() || filePath;
  return basename.replace(/\.md$/i, '').replace(/[-_]/g, ' ');
}

// Language detection
const LANG_EXTENSIONS: Record<string, string[]> = {
  typescript: ['.ts', '.tsx'],
  javascript: ['.js', '.jsx', '.mjs'],
  python: ['.py']
};

function detectLanguage(filePath: string): string | undefined {
  const ext = extname(filePath).toLowerCase();
  for (const [lang, exts] of Object.entries(LANG_EXTENSIONS)) {
    if (exts.includes(ext)) return lang;
  }
  return undefined;
}

// Walk directory
function walkDir(dir: string, patterns: string[], excludePatterns: string[]): string[] {
  const files: string[] = [];

  function matchesPattern(path: string, pattern: string): boolean {
    if (pattern.startsWith('**/')) {
      const suffix = pattern.slice(3);
      return path.endsWith(suffix.replace('*', ''));
    }
    if (pattern.startsWith('*.')) {
      return path.endsWith(pattern.slice(1));
    }
    return path.includes(pattern);
  }

  function walk(currentDir: string) {
    const entries = readdirSync(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(currentDir, entry.name);
      const relativePath = relative(dir, fullPath);

      if (excludePatterns.some(p => matchesPattern(relativePath, p))) {
        continue;
      }

      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.isFile()) {
        if (patterns.some(p => matchesPattern(relativePath, p))) {
          files.push(fullPath);
        }
      }
    }
  }

  walk(dir);
  return files;
}

// Relationship type inference
function inferRelType(sourceType: string, targetType: string): string {
  if (sourceType === 'architecture' && targetType === 'requirements') return 'ADDRESSES';
  if (sourceType === 'architecture' && targetType === 'design') return 'GUIDES';
  if (sourceType === 'design' && targetType === 'requirements') return 'IMPLEMENTS';
  if (sourceType === 'design' && targetType === 'architecture') return 'FOLLOWS';
  if (sourceType === 'requirements' && targetType === 'design') return 'IMPLEMENTED_BY';
  if (sourceType === 'component' && targetType === 'design') return 'IMPLEMENTS';
  return 'RELATED_TO';
}

async function main() {
  console.log('Loading configuration...');
  const config = loadConfig();

  console.log('Initializing adapters...');
  const qdrant = new QdrantAdapter(config.qdrant.url, PROJECT_ID);
  const neo4j = new Neo4jAdapter(
    config.neo4j.uri,
    config.neo4j.user,
    config.neo4j.password,
    PROJECT_ID
  );
  const voyage = new VoyageClient(config.voyage.api_key);

  await neo4j.verifyConnectivity();

  // Ensure collections exist
  console.log('Ensuring collections...');
  await qdrant.ensureAllCollections();

  // Index documentation
  console.log('\n=== Indexing Documentation ===');
  const docDirs = [
    { path: join(PROJECT_ROOT, 'requirement-docs'), type: 'documentation' },
    { path: join(PROJECT_ROOT, 'design-docs'), type: 'documentation' },
    { path: join(PROJECT_ROOT, 'project-docs'), type: 'documentation' },
    { path: join(PROJECT_ROOT, 'user-docs'), type: 'documentation' }
  ];

  const indexedDocs: Array<{ id: string; type: string; embedding: number[] }> = [];

  for (const { path: dirPath } of docDirs) {
    if (!existsSync(dirPath)) continue;

    const files = walkDir(dirPath, ['**/*.md'], ['**/README.md', '**/_sample*.md', '**/node_modules/**']);
    console.log(`Found ${files.length} markdown files in ${dirPath}`);

    for (const filePath of files) {
      try {
        const content = readFileSync(filePath, 'utf-8');
        const docType = detectDocType(filePath);
        const title = extractTitle(content, filePath);
        const memoryId = randomUUID();
        const now = new Date().toISOString();

        console.log(`  [${docType}] ${title}`);

        const embedding = await voyage.embed(content);
        const collection = `${PROJECT_ID}_${docType}`;

        await qdrant.upsert(collection, {
          id: memoryId,
          vector: embedding,
          payload: {
            type: docType,
            content: content,
            metadata: {
              file_path: filePath,
              document: title,
              size_bytes: Buffer.byteLength(content, 'utf-8'),
              indexed_at: now
            },
            created_at: now,
            updated_at: now,
            deleted: false,
            project_id: PROJECT_ID
          }
        });

        // Create Neo4j node for graph-eligible types
        if (['requirements', 'design', 'architecture'].includes(docType)) {
          await neo4j.createNode(
            docType.charAt(0).toUpperCase() + docType.slice(1),
            memoryId,
            {
              content: content.substring(0, 500),
              document: title,
              file_path: filePath
            }
          );

          indexedDocs.push({ id: memoryId, type: docType, embedding });
        }
      } catch (err) {
        console.error(`  Error indexing ${filePath}:`, err);
      }
    }
  }

  // Create relationships between documents
  console.log('\n=== Creating Relationships ===');
  for (const doc of indexedDocs) {
    const searchTypes = ['requirements', 'design', 'architecture'].filter(t => t !== doc.type);

    for (const targetType of searchTypes) {
      try {
        const similar = await qdrant.searchSimilar(
          `${PROJECT_ID}_${targetType}`,
          doc.embedding,
          3,
          0.7
        );

        for (const match of similar) {
          const relType = inferRelType(doc.type, targetType);
          try {
            await neo4j.createRelationship(doc.id, relType, match.id);
            console.log(`  ${doc.type} --[${relType}]--> ${targetType} (score: ${match.score.toFixed(3)})`);
          } catch {
            // Relationship may already exist
          }
        }
      } catch {
        // Collection may not exist
      }
    }
  }

  // Index source code
  console.log('\n=== Indexing Source Code ===');
  const codeDirs = [
    join(PROJECT_ROOT, 'mcp-server/src'),
    join(PROJECT_ROOT, 'inspector-ui/src'),
    join(PROJECT_ROOT, 'inspector-ui/server')
  ];

  for (const dirPath of codeDirs) {
    if (!existsSync(dirPath)) continue;

    const files = walkDir(dirPath, ['**/*.ts', '**/*.tsx'], ['**/*.test.ts', '**/*.d.ts', '**/node_modules/**', '**/dist/**']);
    console.log(`Found ${files.length} code files in ${dirPath}`);

    for (const filePath of files) {
      try {
        const content = readFileSync(filePath, 'utf-8');
        const language = detectLanguage(filePath);
        const memoryId = randomUUID();
        const now = new Date().toISOString();
        const relativePath = relative(PROJECT_ROOT, filePath);

        console.log(`  [code] ${relativePath}`);

        const embedding = await voyage.embed(content);
        const collection = `${PROJECT_ID}_code_pattern`;

        await qdrant.upsert(collection, {
          id: memoryId,
          vector: embedding,
          payload: {
            type: 'code_pattern',
            content: content,
            metadata: {
              file_path: filePath,
              language: language,
              size_bytes: Buffer.byteLength(content, 'utf-8'),
              indexed_at: now
            },
            created_at: now,
            updated_at: now,
            deleted: false,
            project_id: PROJECT_ID
          }
        });
      } catch (err) {
        console.error(`  Error indexing ${filePath}:`, err);
      }
    }
  }

  // Print summary
  console.log('\n=== Summary ===');
  const stats = await qdrant.getStatistics();
  for (const col of stats.collections) {
    if (col.count > 0) {
      console.log(`  ${col.name}: ${col.count} items`);
    }
  }

  const neo4jStats = await neo4j.getStatistics();
  console.log(`  Neo4j: ${neo4jStats.nodeCount} nodes, ${neo4jStats.relationshipCount} relationships`);

  await neo4j.close();
  console.log('\nDone!');
}

main().catch(console.error);
