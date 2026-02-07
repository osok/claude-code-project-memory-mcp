/**
 * Keyboard Shortcuts
 *
 * Global keyboard shortcut handler and help dialog.
 */
import { useEffect, useCallback, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Keyboard, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/ui-store';

// Define all keyboard shortcuts
export const SHORTCUTS = [
  {
    key: 'g b',
    description: 'Go to Browser',
    category: 'Navigation'
  },
  {
    key: 'g s',
    description: 'Go to Search',
    category: 'Navigation'
  },
  {
    key: 'g g',
    description: 'Go to Graph',
    category: 'Navigation'
  },
  {
    key: 'g m',
    description: 'Go to Maintenance',
    category: 'Navigation'
  },
  {
    key: 'g ,',
    description: 'Go to Settings',
    category: 'Navigation'
  },
  {
    key: '/',
    description: 'Focus search',
    category: 'Actions'
  },
  {
    key: 'Escape',
    description: 'Close dialog/panel',
    category: 'Actions'
  },
  {
    key: '?',
    description: 'Show keyboard shortcuts',
    category: 'Help'
  }
] as const;

/**
 * Hook for handling keyboard shortcuts
 */
export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const location = useLocation();
  const { closeDetailPanel, showShortcutsHelp, setShowShortcutsHelp } = useUIStore();

  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Ignore if typing in input/textarea
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      // Exception: Escape should still work
      if (event.key !== 'Escape') {
        return;
      }
    }

    // Handle Escape
    if (event.key === 'Escape') {
      event.preventDefault();
      closeDetailPanel();
      setShowShortcutsHelp(false);
      setPendingKey(null);
      return;
    }

    // Handle ? for help
    if (event.key === '?' && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      setShowShortcutsHelp(true);
      return;
    }

    // Handle / for search focus
    if (event.key === '/' && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      const searchInput = document.querySelector<HTMLInputElement>(
        'input[type="search"], input[placeholder*="Search"]'
      );
      searchInput?.focus();
      return;
    }

    // Handle chord shortcuts (g + letter)
    if (pendingKey === 'g') {
      event.preventDefault();
      setPendingKey(null);

      switch (event.key) {
        case 'b':
          navigate('/browser');
          break;
        case 's':
          navigate('/search');
          break;
        case 'g':
          navigate('/graph');
          break;
        case 'm':
          navigate('/maintenance');
          break;
        case ',':
          navigate('/settings');
          break;
      }
      return;
    }

    // Start chord with 'g'
    if (event.key === 'g' && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      setPendingKey('g');
      // Clear pending key after timeout
      setTimeout(() => setPendingKey(null), 1000);
      return;
    }
  }, [navigate, closeDetailPanel, setShowShortcutsHelp, pendingKey]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return {
    pendingKey,
    showHelp: () => setShowShortcutsHelp(true)
  };
}

/**
 * Keyboard shortcuts help dialog
 */
export function KeyboardShortcutsHelp() {
  const { showShortcutsHelp, setShowShortcutsHelp } = useUIStore();

  if (!showShortcutsHelp) return null;

  // Group shortcuts by category
  const groupedShortcuts = SHORTCUTS.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = [];
    }
    acc[shortcut.category].push(shortcut);
    return acc;
  }, {} as Record<string, typeof SHORTCUTS[number][]>);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={() => setShowShortcutsHelp(false)}
    >
      <div
        className="bg-background rounded-lg shadow-lg w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            <h2 className="font-semibold">Keyboard Shortcuts</h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowShortcutsHelp(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
            <div key={category} className="mb-4 last:mb-0">
              <h3 className="text-sm font-medium text-muted-foreground mb-2">
                {category}
              </h3>
              <div className="space-y-2">
                {shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.key}
                    className="flex items-center justify-between"
                  >
                    <span className="text-sm">{shortcut.description}</span>
                    <kbd className="px-2 py-1 text-xs font-mono bg-muted rounded">
                      {shortcut.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-muted/50">
          <p className="text-xs text-muted-foreground text-center">
            Press <kbd className="px-1 py-0.5 bg-muted rounded text-[10px]">?</kbd> anytime to show this dialog
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Pending key indicator
 */
interface PendingKeyIndicatorProps {
  pendingKey: string | null;
}

export function PendingKeyIndicator({ pendingKey }: PendingKeyIndicatorProps) {
  if (!pendingKey) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
      <div className="bg-foreground text-background px-3 py-1.5 rounded-md shadow-lg">
        <span className="text-sm font-mono">
          {pendingKey} + <span className="animate-pulse">_</span>
        </span>
      </div>
    </div>
  );
}

export default {
  useKeyboardShortcuts,
  KeyboardShortcutsHelp,
  PendingKeyIndicator
};
