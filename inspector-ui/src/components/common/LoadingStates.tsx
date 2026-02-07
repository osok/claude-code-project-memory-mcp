/**
 * Loading States Components
 *
 * Various loading indicators and skeleton loaders.
 */
import { cn } from '@/lib/utils';

/**
 * Spinner component
 */
interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  };

  return (
    <div
      className={cn(
        'animate-spin rounded-full border-2 border-muted border-t-primary',
        sizeClasses[size],
        className
      )}
    />
  );
}

/**
 * Full page loading overlay
 */
interface PageLoadingProps {
  message?: string;
}

export function PageLoading({ message = 'Loading...' }: PageLoadingProps) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
      <Spinner size="lg" />
      <p className="mt-4 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

/**
 * Inline loading indicator
 */
interface InlineLoadingProps {
  className?: string;
}

export function InlineLoading({ className }: InlineLoadingProps) {
  return (
    <div className={cn('flex items-center justify-center p-4', className)}>
      <Spinner size="sm" />
      <span className="ml-2 text-sm text-muted-foreground">Loading...</span>
    </div>
  );
}

/**
 * Skeleton base component
 */
interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
    />
  );
}

/**
 * Skeleton for a text line
 */
interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

export function SkeletonText({ lines = 1, className }: SkeletonTextProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for a table row
 */
interface SkeletonTableRowProps {
  columns?: number;
}

export function SkeletonTableRow({ columns = 5 }: SkeletonTableRowProps) {
  return (
    <tr className="border-b">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="p-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

/**
 * Skeleton for the memory list
 */
interface SkeletonMemoryListProps {
  rows?: number;
}

export function SkeletonMemoryList({ rows = 5 }: SkeletonMemoryListProps) {
  return (
    <div className="rounded-md border">
      {/* Header */}
      <div className="flex items-center gap-3 p-3 border-b bg-muted/50">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 flex-1" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-24" />
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 border-b last:border-0">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton for a card
 */
export function SkeletonCard() {
  return (
    <div className="rounded-md border p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <Skeleton className="h-20 w-full" />
      <div className="flex gap-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

/**
 * Skeleton for stats cards
 */
export function SkeletonStatsCards() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-md border p-4 space-y-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-24" />
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton for a detail panel
 */
export function SkeletonDetailPanel() {
  return (
    <div className="space-y-4 p-4">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-6 w-24 rounded-full" />
        <Skeleton className="h-4 w-48" />
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-20" />
      </div>

      {/* Content */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-32 w-full" />
      </div>

      {/* Metadata */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-20" />
        <div className="space-y-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 flex-1" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Progress bar component
 */
interface ProgressBarProps {
  value: number;
  max?: number;
  showLabel?: boolean;
  className?: string;
}

export function ProgressBar({ value, max = 100, showLabel = false, className }: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn('w-full', className)}>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-muted-foreground mt-1">
          {Math.round(percentage)}%
        </p>
      )}
    </div>
  );
}

/**
 * Indeterminate progress bar
 */
interface IndeterminateProgressProps {
  className?: string;
}

export function IndeterminateProgress({ className }: IndeterminateProgressProps) {
  return (
    <div className={cn('w-full h-2 bg-muted rounded-full overflow-hidden', className)}>
      <div className="h-full w-1/3 bg-primary animate-indeterminate" />
    </div>
  );
}

export default {
  Spinner,
  PageLoading,
  InlineLoading,
  Skeleton,
  SkeletonText,
  SkeletonTableRow,
  SkeletonMemoryList,
  SkeletonCard,
  SkeletonStatsCards,
  SkeletonDetailPanel,
  ProgressBar,
  IndeterminateProgress
};
