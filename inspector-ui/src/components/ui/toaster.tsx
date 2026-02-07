import { useUIStore } from '@/stores/ui-store';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

export function Toaster() {
  const { toasts, removeToast } = useUIStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'flex items-start gap-3 rounded-lg border p-4 shadow-lg transition-all',
            'bg-background text-foreground',
            toast.variant === 'destructive' && 'border-destructive bg-destructive/10',
            toast.variant === 'success' && 'border-green-500 bg-green-500/10'
          )}
        >
          <div className="flex-1">
            <p className="font-semibold">{toast.title}</p>
            {toast.description && (
              <p className="mt-1 text-sm text-muted-foreground">{toast.description}</p>
            )}
          </div>
          <button
            onClick={() => removeToast(toast.id)}
            className="rounded-md p-1 hover:bg-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
