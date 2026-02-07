/**
 * Delete Confirmation Dialog
 *
 * Confirmation dialog for deleting memories with soft/hard delete option.
 */
import { useState } from 'react';
import { Trash2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { truncate } from '@/lib/utils';
import type { Memory, MemoryType } from '@/types';

interface DeleteConfirmationProps {
  memories: Memory[];
  onConfirm: (hard: boolean) => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export function DeleteConfirmation({
  memories,
  onConfirm,
  onCancel,
  isDeleting = false
}: DeleteConfirmationProps) {
  const [hardDelete, setHardDelete] = useState(false);

  const isBulk = memories.length > 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background rounded-lg shadow-lg w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center gap-3 p-4 border-b">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-destructive/10">
            <Trash2 className="h-5 w-5 text-destructive" />
          </div>
          <div>
            <h2 className="font-semibold">
              Delete {isBulk ? `${memories.length} memories` : 'memory'}?
            </h2>
            <p className="text-sm text-muted-foreground">
              {hardDelete ? 'This action cannot be undone' : 'Memory will be marked as deleted'}
            </p>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Preview */}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {memories.slice(0, 5).map((memory) => (
              <div
                key={memory.memory_id}
                className="flex items-center gap-2 p-2 rounded bg-muted/50"
              >
                <Badge variant={memory.type as MemoryType} className="shrink-0">
                  {memory.type}
                </Badge>
                <span className="text-sm truncate">
                  {truncate(memory.content, 50)}
                </span>
              </div>
            ))}
            {memories.length > 5 && (
              <p className="text-sm text-muted-foreground text-center">
                + {memories.length - 5} more
              </p>
            )}
          </div>

          {/* Hard delete option */}
          <label className="flex items-start gap-3 p-3 rounded border cursor-pointer hover:bg-muted/50">
            <input
              type="checkbox"
              checked={hardDelete}
              onChange={(e) => setHardDelete(e.target.checked)}
              className="mt-1"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">Permanently delete</span>
                <AlertTriangle className="h-4 w-4 text-destructive" />
              </div>
              <p className="text-sm text-muted-foreground">
                Permanently remove from database. Cannot be recovered.
              </p>
            </div>
          </label>

          {hardDelete && (
            <div className="flex items-start gap-2 p-3 rounded bg-destructive/10 text-destructive">
              <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
              <p className="text-sm">
                Warning: Hard delete will permanently remove {isBulk ? 'these memories' : 'this memory'} from
                both Qdrant and Neo4j. This action cannot be undone!
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 p-4 border-t">
          <Button variant="outline" onClick={onCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => onConfirm(hardDelete)}
            disabled={isDeleting}
          >
            {isDeleting ? (
              'Deleting...'
            ) : hardDelete ? (
              'Permanently Delete'
            ) : (
              'Delete'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default DeleteConfirmation;
