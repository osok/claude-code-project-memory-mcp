/**
 * Settings Page
 *
 * Project selection and connection configuration.
 */
import { useState } from 'react';
import { Check, X, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useConfigStore } from '@/stores/config-store';
import { useTestConnections } from '@/hooks/use-stats';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
  const {
    projectId,
    recentProjects,
    setProjectId,
    removeRecentProject,
    qdrantUrl,
    neo4jUri,
    neo4jUser,
    setConnection,
    pageSize,
    setPageSize
  } = useConfigStore();

  const [newProjectId, setNewProjectId] = useState(projectId);
  const testConnections = useTestConnections();

  const handleProjectChange = () => {
    if (newProjectId.trim()) {
      setProjectId(newProjectId.trim());
    }
  };

  return (
    <div className="max-w-2xl space-y-8">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Project Selection */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Project</h2>
        <div className="rounded-md border p-4 space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Project ID"
              value={newProjectId}
              onChange={(e) => setNewProjectId(e.target.value)}
            />
            <Button onClick={handleProjectChange}>Apply</Button>
          </div>

          {recentProjects.length > 1 && (
            <div>
              <p className="text-sm text-muted-foreground mb-2">Recent projects:</p>
              <div className="flex flex-wrap gap-2">
                {recentProjects.map((p) => (
                  <div
                    key={p}
                    className={cn(
                      'flex items-center gap-1 px-2 py-1 rounded text-sm',
                      p === projectId ? 'bg-primary text-primary-foreground' : 'bg-muted'
                    )}
                  >
                    <button onClick={() => setProjectId(p)}>{p}</button>
                    {p !== 'default' && p !== projectId && (
                      <button
                        onClick={() => removeRecentProject(p)}
                        className="ml-1 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Connection Settings */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Connections</h2>
        <div className="rounded-md border p-4 space-y-4">
          <div className="grid gap-4">
            <div>
              <label className="text-sm font-medium">Qdrant URL</label>
              <Input
                placeholder="http://localhost:6333"
                value={qdrantUrl}
                onChange={(e) => setConnection('qdrantUrl', e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Neo4j URI</label>
              <Input
                placeholder="bolt://localhost:7687"
                value={neo4jUri}
                onChange={(e) => setConnection('neo4jUri', e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Neo4j Username</label>
              <Input
                placeholder="neo4j"
                value={neo4jUser}
                onChange={(e) => setConnection('neo4jUser', e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Neo4j Password</label>
              <Input
                type="password"
                placeholder="Enter password"
                onChange={(e) => setConnection('neo4jPassword', e.target.value)}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Password is not persisted to localStorage
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">Voyage API Key</label>
              <Input
                type="password"
                placeholder="Enter API key"
                onChange={(e) => setConnection('voyageApiKey', e.target.value)}
              />
              <p className="text-xs text-muted-foreground mt-1">
                API key is not persisted to localStorage
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            onClick={() => testConnections.mutate()}
            disabled={testConnections.isPending}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', testConnections.isPending && 'animate-spin')} />
            Test Connections
          </Button>

          {testConnections.data && (
            <div className="grid grid-cols-3 gap-4 mt-4">
              {Object.entries(testConnections.data.connections).map(([name, result]) => (
                <div key={name} className="flex items-center gap-2">
                  {result.status === 'ok' ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <X className="h-4 w-4 text-red-600" />
                  )}
                  <span className="text-sm capitalize">{name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* UI Preferences */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Preferences</h2>
        <div className="rounded-md border p-4 space-y-4">
          <div>
            <label className="text-sm font-medium">Default Page Size</label>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="ml-2 h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      </section>
    </div>
  );
}
