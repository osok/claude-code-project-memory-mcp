/**
 * Config Store
 *
 * Zustand store for configuration with localStorage persistence.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ConfigState {
  // Project
  projectId: string;
  recentProjects: string[];

  // Connections (runtime overrides)
  qdrantUrl: string;
  neo4jUri: string;
  neo4jUser: string;
  neo4jPassword: string;
  voyageApiKey: string;

  // UI Preferences
  pageSize: number;
  columnVisibility: Record<string, boolean>;

  // Actions
  setProjectId: (id: string) => void;
  addRecentProject: (id: string) => void;
  removeRecentProject: (id: string) => void;

  setConnection: (key: 'qdrantUrl' | 'neo4jUri' | 'neo4jUser' | 'neo4jPassword' | 'voyageApiKey', value: string) => void;
  clearConnections: () => void;

  setPageSize: (size: number) => void;
  setColumnVisibility: (column: string, visible: boolean) => void;
  resetColumnVisibility: () => void;
}

const defaultColumnVisibility: Record<string, boolean> = {
  checkbox: true,
  id: true,
  type: true,
  content: true,
  created_at: true,
  updated_at: true
};

export const useConfigStore = create<ConfigState>()(
  persist(
    (set, get) => ({
      // Project
      projectId: 'default',
      recentProjects: ['default'],

      // Connections
      qdrantUrl: '',
      neo4jUri: '',
      neo4jUser: '',
      neo4jPassword: '',
      voyageApiKey: '',

      // UI Preferences
      pageSize: 25,
      columnVisibility: defaultColumnVisibility,

      // Project actions
      setProjectId: (id) => {
        const prevId = get().projectId;
        set({ projectId: id });
        get().addRecentProject(id);

        // Notify listeners of project change (for cache invalidation)
        if (prevId !== id) {
          window.dispatchEvent(new CustomEvent('project-changed', { detail: { projectId: id, previousProjectId: prevId } }));
        }
      },

      addRecentProject: (id) => set(state => {
        const recent = [id, ...state.recentProjects.filter(p => p !== id)].slice(0, 10);
        return { recentProjects: recent };
      }),

      removeRecentProject: (id) => set(state => ({
        recentProjects: state.recentProjects.filter(p => p !== id)
      })),

      // Connection actions
      setConnection: (key, value) => set({ [key]: value }),

      clearConnections: () => set({
        qdrantUrl: '',
        neo4jUri: '',
        neo4jUser: '',
        neo4jPassword: '',
        voyageApiKey: ''
      }),

      // Preference actions
      setPageSize: (size) => set({ pageSize: size }),

      setColumnVisibility: (column, visible) => set(state => ({
        columnVisibility: { ...state.columnVisibility, [column]: visible }
      })),

      resetColumnVisibility: () => set({ columnVisibility: defaultColumnVisibility })
    }),
    {
      name: 'inspector-config-store',
      partialize: (state) => ({
        projectId: state.projectId,
        recentProjects: state.recentProjects,
        qdrantUrl: state.qdrantUrl,
        neo4jUri: state.neo4jUri,
        neo4jUser: state.neo4jUser,
        // Don't persist sensitive credentials to localStorage
        // neo4jPassword: state.neo4jPassword,
        // voyageApiKey: state.voyageApiKey,
        pageSize: state.pageSize,
        columnVisibility: state.columnVisibility
      })
    }
  )
);
