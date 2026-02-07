/**
 * Search Page
 *
 * Semantic search, code search, and duplicate detection.
 */
import { useState } from 'react';
import { Search, Code, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useSemanticSearch, useCodeSearch, useDuplicateSearch } from '@/hooks/use-search';
import { cn, truncate, formatDuration } from '@/lib/utils';
import type { MemoryType, SearchResult, CodeSearchResult, DuplicateResult } from '@/types';

type Tab = 'semantic' | 'code' | 'duplicates';

export default function SearchPage() {
  const [activeTab, setActiveTab] = useState<Tab>('semantic');

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <TabButton
          active={activeTab === 'semantic'}
          onClick={() => setActiveTab('semantic')}
          icon={<Search className="h-4 w-4" />}
          label="Semantic Search"
        />
        <TabButton
          active={activeTab === 'code'}
          onClick={() => setActiveTab('code')}
          icon={<Code className="h-4 w-4" />}
          label="Code Search"
        />
        <TabButton
          active={activeTab === 'duplicates'}
          onClick={() => setActiveTab('duplicates')}
          icon={<Copy className="h-4 w-4" />}
          label="Duplicate Detection"
        />
      </div>

      {/* Tab Content */}
      {activeTab === 'semantic' && <SemanticSearchTab />}
      {activeTab === 'code' && <CodeSearchTab />}
      {activeTab === 'duplicates' && <DuplicateSearchTab />}
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors',
        active
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground'
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function SemanticSearchTab() {
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(25);
  const search = useSemanticSearch();

  const handleSearch = () => {
    if (query.trim()) {
      search.mutate({ query, limit });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <Input
          placeholder="Enter natural language query..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="flex-1"
        />
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="h-10 rounded-md border border-input bg-background px-3"
        >
          <option value={10}>10 results</option>
          <option value={25}>25 results</option>
          <option value={50}>50 results</option>
          <option value={100}>100 results</option>
        </select>
        <Button onClick={handleSearch} disabled={search.isPending}>
          {search.isPending ? 'Searching...' : 'Search'}
        </Button>
      </div>

      {search.data && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {search.data.count} results in {formatDuration(search.data.duration)}
          </p>
          <SearchResults results={search.data.results} />
        </div>
      )}
    </div>
  );
}

function CodeSearchTab() {
  const [code, setCode] = useState('');
  const [threshold, setThreshold] = useState(0.85);
  const search = useCodeSearch();

  const handleSearch = () => {
    if (code.trim()) {
      search.mutate({ code, threshold });
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <textarea
          placeholder="Paste code snippet to find similar code..."
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="h-40 w-full rounded-md border border-input bg-background p-3 font-mono text-sm"
        />
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            Similarity threshold:
            <input
              type="range"
              min="0.7"
              max="0.95"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-32"
            />
            <span className="w-12">{Math.round(threshold * 100)}%</span>
          </label>
          <Button onClick={handleSearch} disabled={search.isPending}>
            {search.isPending ? 'Searching...' : 'Search'}
          </Button>
        </div>
      </div>

      {search.data && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {search.data.count} results in {formatDuration(search.data.duration)}
          </p>
          <CodeSearchResults results={search.data.results} />
        </div>
      )}
    </div>
  );
}

function DuplicateSearchTab() {
  const [content, setContent] = useState('');
  const [type, setType] = useState<string>('requirements');
  const [threshold, setThreshold] = useState(0.9);
  const search = useDuplicateSearch();

  const handleSearch = () => {
    if (content.trim()) {
      search.mutate({ content, type, threshold });
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <textarea
          placeholder="Paste content to check for duplicates..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="h-40 w-full rounded-md border border-input bg-background p-3 text-sm"
        />
        <div className="flex items-center gap-4">
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3"
          >
            <option value="requirements">Requirements</option>
            <option value="design">Design</option>
            <option value="code_pattern">Code Pattern</option>
            <option value="component">Component</option>
            <option value="function">Function</option>
            <option value="test_history">Test History</option>
            <option value="session">Session</option>
            <option value="user_preference">User Preference</option>
          </select>
          <label className="flex items-center gap-2 text-sm">
            Threshold:
            <input
              type="range"
              min="0.8"
              max="0.99"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-32"
            />
            <span className="w-12">{Math.round(threshold * 100)}%</span>
          </label>
          <Button onClick={handleSearch} disabled={search.isPending}>
            {search.isPending ? 'Checking...' : 'Check Duplicates'}
          </Button>
        </div>
      </div>

      {search.data && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {search.data.count} potential duplicates found
          </p>
          <DuplicateResults results={search.data.duplicates} />
        </div>
      )}
    </div>
  );
}

function SearchResults({ results }: { results: SearchResult[] }) {
  if (results.length === 0) {
    return <p className="text-center text-muted-foreground py-8">No results found</p>;
  }

  return (
    <div className="space-y-2">
      {results.map((result) => (
        <div
          key={result.memory.memory_id}
          className="rounded-md border p-3 hover:bg-muted/50 cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-2">
            <ScoreBar score={result.score} />
            <Badge variant={result.memory.type as MemoryType}>{result.memory.type}</Badge>
          </div>
          <p className="text-sm">{truncate(result.memory.content, 200)}</p>
        </div>
      ))}
    </div>
  );
}

function CodeSearchResults({ results }: { results: CodeSearchResult[] }) {
  if (results.length === 0) {
    return <p className="text-center text-muted-foreground py-8">No similar code found</p>;
  }

  return (
    <div className="space-y-2">
      {results.map((result) => (
        <div
          key={result.memory.memory_id}
          className="rounded-md border p-3 hover:bg-muted/50 cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-2">
            <ScoreBar score={result.score} />
            {result.language && (
              <Badge variant="outline">{result.language}</Badge>
            )}
            {result.filePath && (
              <span className="text-xs text-muted-foreground">{result.filePath}</span>
            )}
          </div>
          <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
            {truncate(result.memory.content, 300)}
          </pre>
        </div>
      ))}
    </div>
  );
}

function DuplicateResults({ results }: { results: DuplicateResult[] }) {
  if (results.length === 0) {
    return <p className="text-center text-muted-foreground py-8">No duplicates found</p>;
  }

  return (
    <div className="space-y-2">
      {results.map((result) => (
        <div
          key={result.memory.memory_id}
          className="rounded-md border p-3 hover:bg-muted/50 cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-orange-600">{result.similarity} similar</span>
            <Badge variant={result.memory.type as MemoryType}>{result.memory.type}</Badge>
          </div>
          <p className="text-sm">{truncate(result.memory.content, 200)}</p>
        </div>
      ))}
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground w-8">{percentage}%</span>
    </div>
  );
}
