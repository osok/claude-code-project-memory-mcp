/**
 * Main Application Layout
 *
 * Contains Header, Sidebar, main content area, and Footer.
 */
import { ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';
import { DetailPanel } from './DetailPanel';
import { useUIStore } from '@/stores/ui-store';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { sidebarCollapsed, detailPanelOpen, closeDetailPanel } = useUIStore();

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main
          className={cn(
            'flex-1 overflow-auto p-4 transition-all duration-300',
            sidebarCollapsed ? 'ml-16' : 'ml-64'
          )}
        >
          {children}
        </main>

        <DetailPanel
          isOpen={detailPanelOpen}
          onClose={closeDetailPanel}
          title="Memory Details"
        >
          {/* Content rendered by individual pages */}
        </DetailPanel>
      </div>

      <Footer />
    </div>
  );
}
