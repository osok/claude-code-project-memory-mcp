/**
 * Application Header
 *
 * Contains logo, project selector, and settings button.
 */
import { Database, Settings, Moon, Sun, Monitor } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/ui-store';
import { useConfigStore } from '@/stores/config-store';
import { useProjects } from '@/hooks/use-stats';
import { useQueryClient } from '@tanstack/react-query';

export function Header() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { theme, setTheme } = useUIStore();
  const { projectId, recentProjects, setProjectId, addRecentProject } = useConfigStore();
  const { data: projectsData } = useProjects();

  // Combine available projects with recent projects, removing duplicates
  const availableProjects = projectsData?.projects || [];
  const allProjects = Array.from(new Set([...availableProjects, ...recentProjects])).sort((a, b) => {
    if (a === 'default') return -1;
    if (b === 'default') return 1;
    return a.localeCompare(b);
  });

  const handleProjectChange = (newProjectId: string) => {
    setProjectId(newProjectId);
    addRecentProject(newProjectId);
    // Invalidate all queries to refetch with new project
    queryClient.invalidateQueries();
  };

  const cycleTheme = () => {
    const themes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(theme);
    const nextTheme = themes[(currentIndex + 1) % themes.length];
    setTheme(nextTheme);
  };

  const ThemeIcon = theme === 'dark' ? Moon : theme === 'light' ? Sun : Monitor;

  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-3">
        <Database className="h-6 w-6 text-primary" />
        <h1 className="text-lg font-semibold">Memory Inspector</h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Project Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Project:</span>
          <select
            value={projectId}
            onChange={(e) => handleProjectChange(e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm min-w-[140px]"
          >
            {allProjects.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        {/* Theme Toggle */}
        <Button variant="ghost" size="icon" onClick={cycleTheme} title={`Theme: ${theme}`}>
          <ThemeIcon className="h-5 w-5" />
        </Button>

        {/* Settings Button */}
        <Button variant="ghost" size="icon" onClick={() => navigate('/settings')}>
          <Settings className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
