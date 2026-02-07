/**
 * Cypher Editor Component
 *
 * Custom Cypher query editor with syntax highlighting and results display.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { Play, Square, History, Trash2, Download, BarChart3, Network } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCypherQuery } from '@/hooks/use-graph';
import { cn } from '@/lib/utils';
import type { CypherQueryResponse } from '@/api/graph';

// Sample queries for quick access
const SAMPLE_QUERIES = [
  {
    name: 'All requirements',
    query: 'MATCH (n:Memory {type: "requirements"}) RETURN n LIMIT 25'
  },
  {
    name: 'Implementation chains',
    query: 'MATCH path = (req:Memory {type: "requirements"})-[:IMPLEMENTS*1..2]-(impl) RETURN path LIMIT 50'
  },
  {
    name: 'Orphan nodes',
    query: 'MATCH (n:Memory) WHERE NOT (n)--() RETURN n LIMIT 50'
  },
  {
    name: 'Most connected',
    query: 'MATCH (n:Memory)-[r]-() RETURN n, count(r) as connections ORDER BY connections DESC LIMIT 20'
  },
  {
    name: 'Test coverage',
    query: 'MATCH (t:Memory {type: "test_history"})-[:TESTS]->(c:Memory) RETURN t, c LIMIT 50'
  }
];

type ResultView = 'table' | 'graph';

interface CypherEditorProps {
  onGraphResult?: (result: CypherQueryResponse['graph']) => void;
  className?: string;
}

export function CypherEditor({ onGraphResult, className }: CypherEditorProps) {
  const [query, setQuery] = useState('');
  const [resultView, setResultView] = useState<ResultView>('table');
  const [queryHistory, setQueryHistory] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('cypher-history') || '[]');
    } catch {
      return [];
    }
  });
  const [showHistory, setShowHistory] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const { mutate: executeCypher, data: result, isPending, error, reset } = useCypherQuery();

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [query]);

  // Save history to localStorage
  const saveHistory = useCallback((newQuery: string) => {
    const updated = [newQuery, ...queryHistory.filter(q => q !== newQuery)].slice(0, 20);
    setQueryHistory(updated);
    localStorage.setItem('cypher-history', JSON.stringify(updated));
  }, [queryHistory]);

  const handleExecute = useCallback(() => {
    if (!query.trim() || isPending) return;

    // Create abort controller for cancellation
    abortControllerRef.current = new AbortController();

    executeCypher(
      { cypher: query.trim() },
      {
        onSuccess: (data) => {
          saveHistory(query.trim());
          if (resultView === 'graph' && onGraphResult) {
            onGraphResult(data.graph);
          }
        }
      }
    );
  }, [query, isPending, executeCypher, saveHistory, resultView, onGraphResult]);

  const handleCancel = useCallback(() => {
    abortControllerRef.current?.abort();
    reset();
  }, [reset]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Ctrl/Cmd + Enter to execute
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleExecute();
    }
  }, [handleExecute]);

  const handleSampleQuery = (sampleQuery: string) => {
    setQuery(sampleQuery);
    setShowHistory(false);
  };

  const handleHistorySelect = (historicalQuery: string) => {
    setQuery(historicalQuery);
    setShowHistory(false);
  };

  const clearHistory = () => {
    setQueryHistory([]);
    localStorage.removeItem('cypher-history');
  };

  const handleClearResults = () => {
    reset();
  };

  const handleExportResults = () => {
    if (!result) return;

    const csv = [
      result.columns.join(','),
      ...result.rows.map(row =>
        result.columns.map(col => {
          const val = row[col];
          const str = typeof val === 'object' ? JSON.stringify(val) : String(val ?? '');
          return `"${str.replace(/"/g, '""')}"`;
        }).join(',')
      )
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cypher-results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={cn('rounded-md border bg-card', className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <h3 className="font-medium">Cypher Query Editor</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Execute read-only Cypher queries against Neo4j
        </p>
      </div>

      {/* Query input */}
      <div className="p-4 border-b">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="MATCH (n:Memory) RETURN n LIMIT 25"
            className={cn(
              'w-full min-h-[100px] p-3 font-mono text-sm',
              'bg-muted/50 rounded-md border',
              'focus:outline-none focus:ring-2 focus:ring-ring',
              'resize-none'
            )}
          />

          {/* Sample queries dropdown */}
          <div className="absolute right-2 top-2">
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
              >
                <History className="h-4 w-4" />
              </Button>

              {showHistory && (
                <div className="absolute right-0 top-full mt-1 w-64 bg-popover border rounded-md shadow-lg z-10">
                  <div className="p-2 border-b">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium">Query History</span>
                      {queryHistory.length > 0 && (
                        <button
                          onClick={clearHistory}
                          className="text-xs text-destructive hover:underline"
                        >
                          Clear
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="max-h-48 overflow-y-auto">
                    {queryHistory.length === 0 ? (
                      <p className="p-2 text-xs text-muted-foreground">No history</p>
                    ) : (
                      queryHistory.map((q, i) => (
                        <button
                          key={i}
                          onClick={() => handleHistorySelect(q)}
                          className="w-full p-2 text-left text-xs font-mono hover:bg-muted truncate"
                        >
                          {q}
                        </button>
                      ))
                    )}
                  </div>

                  <div className="p-2 border-t">
                    <span className="text-xs font-medium text-muted-foreground">
                      Sample Queries
                    </span>
                  </div>
                  {SAMPLE_QUERIES.map((sample, i) => (
                    <button
                      key={i}
                      onClick={() => handleSampleQuery(sample.query)}
                      className="w-full p-2 text-left text-xs hover:bg-muted"
                    >
                      {sample.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-3">
          {isPending ? (
            <Button variant="destructive" size="sm" onClick={handleCancel}>
              <Square className="h-4 w-4 mr-2" />
              Cancel
            </Button>
          ) : (
            <Button size="sm" onClick={handleExecute} disabled={!query.trim()}>
              <Play className="h-4 w-4 mr-2" />
              Execute
            </Button>
          )}

          <span className="text-xs text-muted-foreground">
            Ctrl+Enter to run
          </span>

          {result && (
            <>
              <div className="ml-auto flex items-center gap-1 border rounded-md p-1">
                <Button
                  variant={resultView === 'table' ? 'secondary' : 'ghost'}
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => setResultView('table')}
                >
                  <BarChart3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={resultView === 'graph' ? 'secondary' : 'ghost'}
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => {
                    setResultView('graph');
                    if (result.graph && onGraphResult) {
                      onGraphResult(result.graph);
                    }
                  }}
                >
                  <Network className="h-4 w-4" />
                </Button>
              </div>

              <Button variant="ghost" size="sm" onClick={handleExportResults}>
                <Download className="h-4 w-4" />
              </Button>

              <Button variant="ghost" size="sm" onClick={handleClearResults}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="p-4">
        {isPending && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
            <span className="ml-2 text-sm">Executing query...</span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-md bg-destructive/10 text-destructive">
            <p className="font-medium">Query Error</p>
            <p className="text-sm mt-1">{(error as Error).message}</p>
          </div>
        )}

        {result && resultView === 'table' && (
          <div className="space-y-2">
            {/* Stats */}
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>{result.rowCount} rows</span>
              <span>{result.duration}ms</span>
            </div>

            {/* Table */}
            {result.rows.length > 0 ? (
              <div className="overflow-x-auto border rounded-md">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      {result.columns.map((col) => (
                        <th key={col} className="px-3 py-2 text-left font-medium">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.slice(0, 100).map((row, i) => (
                      <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
                        {result.columns.map((col) => (
                          <td key={col} className="px-3 py-2 font-mono text-xs">
                            <CellValue value={row[col]} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {result.rows.length > 100 && (
                  <p className="p-2 text-xs text-muted-foreground text-center">
                    Showing first 100 of {result.rowCount} rows
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                Query returned no results
              </p>
            )}
          </div>
        )}

        {result && resultView === 'graph' && (
          <div className="text-center py-8 text-muted-foreground">
            <Network className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">Graph view - {result.graph.nodes.length} nodes, {result.graph.edges.length} edges</p>
            <p className="text-xs mt-1">Results displayed in the main graph canvas</p>
          </div>
        )}

        {!isPending && !error && !result && (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">Enter a Cypher query and click Execute</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface CellValueProps {
  value: unknown;
}

function CellValue({ value }: CellValueProps) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }

  if (typeof value === 'boolean') {
    return <Badge variant={value ? 'default' : 'secondary'}>{String(value)}</Badge>;
  }

  if (typeof value === 'number') {
    return <span>{value.toLocaleString()}</span>;
  }

  if (typeof value === 'object') {
    // Check if it's a Neo4j node representation
    if ('type' in (value as Record<string, unknown>) && 'memory_id' in (value as Record<string, unknown>)) {
      const node = value as Record<string, unknown>;
      return (
        <div className="flex items-center gap-1">
          <Badge variant={(node.type as string) || 'default'}>{node.type as string}</Badge>
          <span className="truncate max-w-[200px]">{node.memory_id as string}</span>
        </div>
      );
    }

    const json = JSON.stringify(value, null, 2);
    return (
      <pre className="max-w-[300px] max-h-[100px] overflow-auto text-[10px] bg-muted p-1 rounded">
        {json}
      </pre>
    );
  }

  return <span className="truncate max-w-[300px] block">{String(value)}</span>;
}

export default CypherEditor;
