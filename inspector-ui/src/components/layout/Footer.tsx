/**
 * Application Footer
 *
 * Contains connection status indicators.
 */
import { useQuery } from '@tanstack/react-query';
import { Circle } from 'lucide-react';
import { getStats } from '@/api/stats';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';

export function Footer() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 60000 // Refresh every minute
  });

  const qdrantStatus = stats?.connections.qdrant.status ?? 'disconnected';
  const neo4jStatus = stats?.connections.neo4j.status ?? 'disconnected';

  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 flex h-8 items-center justify-between border-t bg-background px-4 text-xs">
      <div className="flex items-center gap-4">
        <StatusIndicator
          label="Qdrant"
          status={qdrantStatus}
          loading={isLoading}
        />
        <StatusIndicator
          label="Neo4j"
          status={neo4jStatus}
          loading={isLoading}
        />
      </div>

      {stats && (
        <div className="flex items-center gap-4 text-muted-foreground">
          <span>{stats.counts.total.toLocaleString()} memories</span>
          <span>Updated {formatRelativeTime(stats.timestamp)}</span>
        </div>
      )}
    </footer>
  );
}

interface StatusIndicatorProps {
  label: string;
  status: 'connected' | 'disconnected' | 'error';
  loading?: boolean;
}

function StatusIndicator({ label, status, loading }: StatusIndicatorProps) {
  const statusColor = {
    connected: 'text-green-500',
    disconnected: 'text-gray-400',
    error: 'text-red-500'
  }[status];

  return (
    <div className="flex items-center gap-1.5">
      <Circle
        className={cn(
          'h-2 w-2',
          loading ? 'animate-pulse text-yellow-500' : statusColor
        )}
        fill="currentColor"
      />
      <span className="text-muted-foreground">{label}</span>
    </div>
  );
}
