/**
 * Maintenance Page
 *
 * Statistics, normalization, export/import, and indexing.
 */
import { useState } from 'react';
import { RefreshCw, Download, Upload, FolderSearch, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useStats, useNormalize, useNormalizeStatus, useExport, useIndexFile, useIndexDirectory, useIndexStatus, useCleanTestResults } from '@/hooks/use-stats';
import { cn, formatBytes } from '@/lib/utils';

type Tab = 'normalize' | 'export' | 'import' | 'index' | 'test-cleanup';

export default function MaintenancePage() {
  const [activeTab, setActiveTab] = useState<Tab>('normalize');
  const { data: stats, isLoading, refetch } = useStats();

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Total Memories"
          value={stats?.counts.total.toLocaleString() || '0'}
          loading={isLoading}
        />
        <StatCard
          title="Qdrant"
          value={stats?.connections.qdrant.status || 'unknown'}
          status={stats?.connections.qdrant.status}
          loading={isLoading}
        />
        <StatCard
          title="Neo4j"
          value={`${stats?.connections.neo4j.nodeCount || 0} nodes`}
          status={stats?.connections.neo4j.status}
          loading={isLoading}
        />
        <StatCard
          title="Storage"
          value={`~${stats?.storage.estimatedMB || 0} MB`}
          loading={isLoading}
        />
      </div>

      {/* Memory Counts by Type */}
      {stats && (
        <div className="rounded-md border p-4">
          <h3 className="font-semibold mb-4">Memory Counts by Type</h3>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(stats.counts.byType).map(([type, count]) => (
              <div key={type} className="flex justify-between items-center">
                <Badge variant={type as never} className="capitalize">
                  {type.replace('_', ' ')}
                </Badge>
                <span className="text-sm font-mono">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <TabButton active={activeTab === 'normalize'} onClick={() => setActiveTab('normalize')}>
          Normalize
        </TabButton>
        <TabButton active={activeTab === 'export'} onClick={() => setActiveTab('export')}>
          Export
        </TabButton>
        <TabButton active={activeTab === 'import'} onClick={() => setActiveTab('import')}>
          Import
        </TabButton>
        <TabButton active={activeTab === 'index'} onClick={() => setActiveTab('index')}>
          Indexing
        </TabButton>
        <TabButton active={activeTab === 'test-cleanup'} onClick={() => setActiveTab('test-cleanup')}>
          Test Cleanup
        </TabButton>
      </div>

      {/* Tab Content */}
      {activeTab === 'normalize' && <NormalizePanel />}
      {activeTab === 'export' && <ExportPanel />}
      {activeTab === 'import' && <ImportPanel />}
      {activeTab === 'index' && <IndexPanel />}
      {activeTab === 'test-cleanup' && <TestCleanupPanel />}
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string;
  status?: 'connected' | 'disconnected' | 'error';
  loading?: boolean;
}

function StatCard({ title, value, status, loading }: StatCardProps) {
  const statusColor = {
    connected: 'text-green-600',
    disconnected: 'text-gray-400',
    error: 'text-red-600'
  }[status || 'connected'];

  return (
    <div className="rounded-md border p-4">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className={cn(
        'text-2xl font-semibold mt-1',
        status && statusColor,
        loading && 'animate-pulse'
      )}>
        {loading ? '...' : value}
      </p>
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
        active
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground'
      )}
    >
      {children}
    </button>
  );
}

function NormalizePanel() {
  const [phases, setPhases] = useState(['dedup', 'orphan_detection', 'cleanup']);
  const [dryRun, setDryRun] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);

  const normalize = useNormalize();
  const { data: jobStatus } = useNormalizeStatus(jobId);

  const handleNormalize = () => {
    normalize.mutate(
      { phases: phases as ('dedup' | 'orphan_detection' | 'cleanup' | 'embedding_refresh')[], dryRun },
      { onSuccess: (data) => setJobId(data.jobId) }
    );
  };

  const togglePhase = (phase: string) => {
    setPhases(prev =>
      prev.includes(phase) ? prev.filter(p => p !== phase) : [...prev, phase]
    );
  };

  return (
    <div className="space-y-4">
      <div className="rounded-md border p-4 space-y-4">
        <h3 className="font-semibold">Phases</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { id: 'dedup', label: 'Deduplication', desc: 'Remove near-duplicate memories (>95% similar)' },
            { id: 'orphan_detection', label: 'Orphan Detection', desc: 'Find graph nodes without vector data' },
            { id: 'cleanup', label: 'Cleanup', desc: 'Remove soft-deleted memories older than 30 days' },
            { id: 'embedding_refresh', label: 'Embedding Refresh', desc: 'Regenerate fallback embeddings' }
          ].map(phase => (
            <label key={phase.id} className="flex items-start gap-2 p-2 rounded border cursor-pointer hover:bg-muted/50">
              <input
                type="checkbox"
                checked={phases.includes(phase.id)}
                onChange={() => togglePhase(phase.id)}
                className="mt-1"
              />
              <div>
                <p className="font-medium">{phase.label}</p>
                <p className="text-xs text-muted-foreground">{phase.desc}</p>
              </div>
            </label>
          ))}
        </div>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          <span className="text-sm">Dry run (preview only, no changes)</span>
        </label>

        <Button onClick={handleNormalize} disabled={normalize.isPending || phases.length === 0}>
          {normalize.isPending ? 'Starting...' : 'Run Normalization'}
        </Button>
      </div>

      {jobStatus && (
        <div className="rounded-md border p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Job Status</h3>
            <Badge variant={jobStatus.status === 'complete' ? 'default' : 'secondary'}>
              {jobStatus.status}
            </Badge>
          </div>
          {jobStatus.results.map((result, i) => (
            <div key={i} className="text-sm">
              <strong>{result.phase}:</strong> {result.count} items
              {result.details.slice(0, 3).map((d, j) => (
                <p key={j} className="text-xs text-muted-foreground ml-4">{d}</p>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ExportPanel() {
  const exportMutation = useExport();

  return (
    <div className="rounded-md border p-4 space-y-4">
      <p className="text-sm text-muted-foreground">
        Export all memories to JSONL format for backup or migration.
      </p>
      <Button onClick={() => exportMutation.mutate({})} disabled={exportMutation.isPending}>
        <Download className="h-4 w-4 mr-2" />
        {exportMutation.isPending ? 'Exporting...' : 'Export All Memories'}
      </Button>
    </div>
  );
}

function ImportPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [conflictResolution, setConflictResolution] = useState<'skip' | 'overwrite' | 'error'>('skip');

  return (
    <div className="rounded-md border p-4 space-y-4">
      <p className="text-sm text-muted-foreground">
        Import memories from a JSONL file.
      </p>
      <input
        type="file"
        accept=".jsonl"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-primary file:text-primary-foreground"
      />
      <div>
        <label className="text-sm font-medium">On conflict:</label>
        <select
          value={conflictResolution}
          onChange={(e) => setConflictResolution(e.target.value as 'skip' | 'overwrite' | 'error')}
          className="ml-2 h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="skip">Skip existing</option>
          <option value="overwrite">Overwrite</option>
          <option value="error">Error on conflict</option>
        </select>
      </div>
      <Button disabled={!file}>
        <Upload className="h-4 w-4 mr-2" />
        Import
      </Button>
    </div>
  );
}

function IndexPanel() {
  const [filePath, setFilePath] = useState('');
  const [dirPath, setDirPath] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);

  const indexFile = useIndexFile();
  const indexDir = useIndexDirectory();
  const { data: jobStatus } = useIndexStatus(jobId);

  return (
    <div className="space-y-4">
      <div className="rounded-md border p-4 space-y-4">
        <h3 className="font-semibold">Index File</h3>
        <div className="flex gap-2">
          <Input
            placeholder="/path/to/file.ts"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
          />
          <Button onClick={() => indexFile.mutate({ path: filePath })} disabled={!filePath || indexFile.isPending}>
            Index
          </Button>
        </div>
      </div>

      <div className="rounded-md border p-4 space-y-4">
        <h3 className="font-semibold">Index Directory</h3>
        <div className="flex gap-2">
          <Input
            placeholder="/path/to/directory"
            value={dirPath}
            onChange={(e) => setDirPath(e.target.value)}
          />
          <Button
            onClick={() => indexDir.mutate({ path: dirPath }, { onSuccess: (d) => setJobId(d.jobId) })}
            disabled={!dirPath || indexDir.isPending}
          >
            <FolderSearch className="h-4 w-4 mr-2" />
            Index
          </Button>
        </div>
      </div>

      {jobStatus && (
        <div className="rounded-md border p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Indexing Progress</h3>
            <Badge>{jobStatus.status}</Badge>
          </div>
          <p className="text-sm">
            {jobStatus.filesProcessed} / {jobStatus.filesTotal} files processed
          </p>
          {jobStatus.errors.length > 0 && (
            <div className="text-sm text-destructive">
              {jobStatus.errors.slice(0, 3).map((e, i) => <p key={i}>{e}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Test Result Cleanup Panel
 * REQ-007-FN-062: Clean old test results from the memory system
 */
function TestCleanupPanel() {
  const [suiteName, setSuiteName] = useState('');
  const [olderThanDays, setOlderThanDays] = useState(30);
  const [keepCount, setKeepCount] = useState(10);
  const [dryRun, setDryRun] = useState(true);
  const [lastResult, setLastResult] = useState<{
    status: string;
    cleaned_count: number;
    details: string[];
  } | null>(null);

  const cleanTestResults = useCleanTestResults();

  const handleClean = () => {
    cleanTestResults.mutate(
      {
        suiteName: suiteName || undefined,
        olderThanDays,
        keepCount,
        dryRun
      },
      {
        onSuccess: (data) => setLastResult(data)
      }
    );
  };

  return (
    <div className="space-y-4">
      <div className="rounded-md border p-4 space-y-4">
        <div>
          <h3 className="font-semibold">Clean Old Test Results</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Remove old test results to keep the memory system clean. Test results are grouped by suite
            and the most recent results per suite are preserved.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Suite Name (optional)</label>
            <Input
              placeholder="e.g., unit-tests, integration"
              value={suiteName}
              onChange={(e) => setSuiteName(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Leave empty to clean all suites
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Older Than (days)</label>
            <Input
              type="number"
              min={0}
              value={olderThanDays}
              onChange={(e) => setOlderThanDays(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              Only clean results older than this many days
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Keep Count (per suite)</label>
            <Input
              type="number"
              min={0}
              value={keepCount}
              onChange={(e) => setKeepCount(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              Always keep the most recent N results per suite
            </p>
          </div>
        </div>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          <span className="text-sm">Dry run (preview only, no deletions)</span>
        </label>

        <Button onClick={handleClean} disabled={cleanTestResults.isPending}>
          <Trash2 className="h-4 w-4 mr-2" />
          {cleanTestResults.isPending ? 'Cleaning...' : 'Clean Test Results'}
        </Button>
      </div>

      {lastResult && (
        <div className="rounded-md border p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Cleanup Results</h3>
            <Badge variant={lastResult.status === 'dry_run' ? 'secondary' : 'default'}>
              {lastResult.status === 'dry_run' ? 'Preview' : 'Complete'}
            </Badge>
          </div>
          <p className="text-sm">
            <strong>{lastResult.cleaned_count}</strong> test results
            {lastResult.status === 'dry_run' ? ' would be' : ''} cleaned
          </p>
          {lastResult.details.length > 0 && (
            <div className="text-sm text-muted-foreground space-y-1">
              {lastResult.details.slice(0, 10).map((d, i) => (
                <p key={i}>{d}</p>
              ))}
              {lastResult.details.length > 10 && (
                <p className="italic">...and {lastResult.details.length - 10} more</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
