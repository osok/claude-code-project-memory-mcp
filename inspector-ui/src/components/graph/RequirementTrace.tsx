/**
 * Requirement Trace Component
 *
 * UI for tracing requirements through implementations and tests.
 */
import { useState } from 'react';
import { Search, FileCode, TestTube2, CheckCircle, XCircle, AlertCircle, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useRequirementTrace } from '@/hooks/use-graph';
import { cn, truncate, getMemoryTypeColor } from '@/lib/utils';
import type { RequirementTrace as RequirementTraceType } from '@/types';

interface RequirementTraceProps {
  onNavigate?: (type: string, id: string) => void;
  onHighlightPath?: (nodeIds: string[]) => void;
  className?: string;
}

export function RequirementTrace({
  onNavigate,
  onHighlightPath,
  className
}: RequirementTraceProps) {
  const [reqId, setReqId] = useState('');
  const [searchedId, setSearchedId] = useState('');

  const { data: trace, isLoading, error } = useRequirementTrace(searchedId);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (reqId.trim()) {
      setSearchedId(reqId.trim());
    }
  };

  const handleClear = () => {
    setReqId('');
    setSearchedId('');
    onHighlightPath?.([]);
  };

  const handleHighlightTrace = () => {
    if (!trace) return;

    const nodeIds = [
      trace.requirement.id,
      ...trace.implementations.map(i => i.id),
      ...trace.tests.map(t => t.id)
    ];
    onHighlightPath?.(nodeIds);
  };

  return (
    <div className={cn('rounded-md border bg-card', className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <h3 className="font-medium flex items-center gap-2">
          <FileCode className="h-4 w-4" />
          Requirement Tracing
        </h3>
        <p className="text-xs text-muted-foreground mt-1">
          Trace a requirement to its implementations and tests
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="p-4 border-b">
        <div className="flex gap-2">
          <Input
            placeholder="REQ-XXX-FN-NNN"
            value={reqId}
            onChange={(e) => setReqId(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" disabled={!reqId.trim() || isLoading}>
            <Search className="h-4 w-4" />
          </Button>
        </div>
        {searchedId && (
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-primary hover:underline mt-2"
          >
            Clear search
          </button>
        )}
      </form>

      {/* Results */}
      <div className="p-4">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
          </div>
        )}

        {error && (
          <div className="text-center py-4">
            <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
            <p className="text-sm text-destructive">
              {(error as Error).message || 'Failed to trace requirement'}
            </p>
          </div>
        )}

        {!isLoading && !error && !trace && searchedId && (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">No requirement found with ID: {searchedId}</p>
          </div>
        )}

        {!isLoading && !error && !trace && !searchedId && (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">Enter a requirement ID to trace</p>
            <p className="text-xs mt-1">Example: REQ-006-FN-001</p>
          </div>
        )}

        {trace && (
          <TraceResults
            trace={trace}
            onNavigate={onNavigate}
            onHighlight={handleHighlightTrace}
          />
        )}
      </div>
    </div>
  );
}

interface TraceResultsProps {
  trace: RequirementTraceType;
  onNavigate?: (type: string, id: string) => void;
  onHighlight?: () => void;
}

function TraceResults({ trace, onNavigate, onHighlight }: TraceResultsProps) {
  const { requirement, implementations, tests, coverage } = trace;

  return (
    <div className="space-y-4">
      {/* Requirement info */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Badge variant="requirements">{requirement.requirementId}</Badge>
          <Button variant="ghost" size="sm" onClick={onHighlight}>
            Highlight in Graph
          </Button>
        </div>
        <p className="text-sm">{truncate(requirement.content, 100)}</p>
      </div>

      {/* Coverage summary */}
      <div className="grid grid-cols-2 gap-2">
        <CoverageCard
          icon={<FileCode className="h-4 w-4" />}
          label="Implemented"
          count={coverage.implementedCount}
          isComplete={coverage.hasImplementation}
        />
        <CoverageCard
          icon={<TestTube2 className="h-4 w-4" />}
          label="Tested"
          count={coverage.testedCount}
          isComplete={coverage.hasCoverage}
        />
      </div>

      {/* Implementations */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-muted-foreground flex items-center gap-1">
          <FileCode className="h-3 w-3" />
          IMPLEMENTATIONS ({implementations.length})
        </h4>
        {implementations.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No implementations found</p>
        ) : (
          <div className="space-y-1">
            {implementations.map((impl) => (
              <TraceItem
                key={impl.id}
                id={impl.id}
                type={impl.type}
                label={impl.label}
                onClick={() => onNavigate?.(impl.type, impl.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Tests */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-muted-foreground flex items-center gap-1">
          <TestTube2 className="h-3 w-3" />
          TESTS ({tests.length})
        </h4>
        {tests.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No tests found</p>
        ) : (
          <div className="space-y-1">
            {tests.map((test) => (
              <TraceItem
                key={test.id}
                id={test.id}
                type={test.type}
                label={test.label}
                onClick={() => onNavigate?.(test.type, test.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface CoverageCardProps {
  icon: React.ReactNode;
  label: string;
  count: number;
  isComplete: boolean;
}

function CoverageCard({ icon, label, count, isComplete }: CoverageCardProps) {
  return (
    <div
      className={cn(
        'p-3 rounded-md border',
        isComplete ? 'bg-green-500/10 border-green-500/30' : 'bg-amber-500/10 border-amber-500/30'
      )}
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm">{label}</span>
        {isComplete ? (
          <CheckCircle className="h-4 w-4 text-green-500 ml-auto" />
        ) : (
          <XCircle className="h-4 w-4 text-amber-500 ml-auto" />
        )}
      </div>
      <p className="text-2xl font-semibold mt-1">{count}</p>
    </div>
  );
}

interface TraceItemProps {
  id: string;
  type: string;
  label: string;
  onClick?: () => void;
}

function TraceItem({ id, type, label, onClick }: TraceItemProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 w-full p-2 rounded hover:bg-muted text-left group"
    >
      <span
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: getMemoryTypeColor(type) }}
      />
      <span className="text-sm truncate flex-1">{truncate(label, 40)}</span>
      <ExternalLink className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100" />
    </button>
  );
}

export default RequirementTrace;
