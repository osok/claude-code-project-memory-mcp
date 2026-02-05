/**
 * UI Store
 *
 * Zustand store for UI state.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive' | 'success';
  duration?: number;
}

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Detail panel
  detailPanelOpen: boolean;
  detailPanelWidth: 'sm' | 'md' | 'lg';
  detailPanelPixelWidth: number;
  openDetailPanel: () => void;
  closeDetailPanel: () => void;
  setDetailPanelWidth: (width: 'sm' | 'md' | 'lg') => void;
  setDetailPanelPixelWidth: (width: number) => void;

  // Theme
  theme: 'light' | 'dark' | 'system';
  setTheme: (theme: 'light' | 'dark' | 'system') => void;

  // Toasts
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;

  // Keyboard shortcuts help
  showShortcutsHelp: boolean;
  setShowShortcutsHelp: (show: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Sidebar
      sidebarCollapsed: false,
      toggleSidebar: () => set(state => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // Detail panel
      detailPanelOpen: false,
      detailPanelWidth: 'md',
      detailPanelPixelWidth: 480,
      openDetailPanel: () => set({ detailPanelOpen: true }),
      closeDetailPanel: () => set({ detailPanelOpen: false }),
      setDetailPanelWidth: (width) => set({ detailPanelWidth: width }),
      setDetailPanelPixelWidth: (width) => set({ detailPanelPixelWidth: Math.max(320, Math.min(800, width)) }),

      // Theme
      theme: 'system',
      setTheme: (theme) => {
        set({ theme });
        applyTheme(theme);
      },

      // Toasts
      toasts: [],
      addToast: (toast) => {
        const id = Math.random().toString(36).slice(2);
        set(state => ({
          toasts: [...state.toasts, { ...toast, id }]
        }));

        // Auto-remove after duration
        const duration = toast.duration ?? 5000;
        if (duration > 0) {
          setTimeout(() => {
            get().removeToast(id);
          }, duration);
        }
      },
      removeToast: (id) => set(state => ({
        toasts: state.toasts.filter(t => t.id !== id)
      })),
      clearToasts: () => set({ toasts: [] }),

      // Keyboard shortcuts help
      showShortcutsHelp: false,
      setShowShortcutsHelp: (show) => set({ showShortcutsHelp: show })
    }),
    {
      name: 'inspector-ui-store',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        detailPanelWidth: state.detailPanelWidth,
        detailPanelPixelWidth: state.detailPanelPixelWidth,
        theme: state.theme
      })
    }
  )
);

// Apply theme to document
function applyTheme(theme: 'light' | 'dark' | 'system') {
  const root = document.documentElement;

  if (theme === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.classList.toggle('dark', prefersDark);
  } else {
    root.classList.toggle('dark', theme === 'dark');
  }
}

// Initialize theme on load
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('inspector-ui-store');
  if (stored) {
    try {
      const state = JSON.parse(stored);
      if (state.state?.theme) {
        applyTheme(state.state.theme);
      }
    } catch {
      // Invalid stored state
    }
  }

  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const currentTheme = useUIStore.getState().theme;
    if (currentTheme === 'system') {
      applyTheme('system');
    }
  });
}
