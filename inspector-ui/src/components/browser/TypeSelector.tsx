/**
 * Type Selector Component
 *
 * Sidebar for selecting memory types with counts.
 */
import { cn, getMemoryTypeColor } from '@/lib/utils';
import { MEMORY_TYPES, type MemoryType } from '@/types';

interface TypeSelectorProps {
  selectedType: MemoryType | 'all';
  counts: Record<string, number>;
  totalCount?: number;
  onSelect: (type: MemoryType | 'all') => void;
}

export function TypeSelector({ selectedType, counts, totalCount, onSelect }: TypeSelectorProps) {
  return (
    <div className="space-y-1">
      {/* All memories option */}
      <TypeButton
        label="All Memories"
        count={totalCount}
        active={selectedType === 'all'}
        onClick={() => onSelect('all')}
      />

      {/* Divider */}
      <div className="my-2 border-t" />

      {/* Memory types */}
      {MEMORY_TYPES.map((type) => (
        <TypeButton
          key={type}
          label={formatTypeName(type)}
          type={type}
          count={counts[type] || 0}
          active={selectedType === type}
          onClick={() => onSelect(type)}
        />
      ))}
    </div>
  );
}

interface TypeButtonProps {
  label: string;
  type?: MemoryType;
  count?: number;
  active: boolean;
  onClick: () => void;
}

function TypeButton({ label, type, count, active, onClick }: TypeButtonProps) {
  const color = type ? getMemoryTypeColor(type) : undefined;

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
        active
          ? 'bg-primary text-primary-foreground'
          : 'hover:bg-accent text-muted-foreground hover:text-accent-foreground'
      )}
    >
      {/* Color indicator */}
      {type && (
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: color }}
        />
      )}

      {/* Label */}
      <span className="flex-1 text-left">{label}</span>

      {/* Count badge */}
      {count !== undefined && (
        <span
          className={cn(
            'text-xs tabular-nums',
            active ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}
        >
          {count.toLocaleString()}
        </span>
      )}
    </button>
  );
}

function formatTypeName(type: string): string {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default TypeSelector;
