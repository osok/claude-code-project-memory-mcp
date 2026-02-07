/**
 * Markdown Renderer Component
 *
 * Renders markdown content with GitHub Flavored Markdown support.
 * Includes syntax highlighting for code blocks and a raw/rendered toggle.
 */
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Code, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SyntaxHighlighter, detectLanguage } from './SyntaxHighlighter';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  defaultView?: 'raw' | 'rendered';
  showToggle?: boolean;
}

/**
 * Detects if content appears to be markdown.
 */
export function isMarkdownContent(content: string): boolean {
  // Check for common markdown patterns
  const markdownPatterns = [
    /^#{1,6}\s+/m,        // Headings
    /^\s*[-*+]\s+/m,       // Unordered lists
    /^\s*\d+\.\s+/m,       // Ordered lists
    /\[.+\]\(.+\)/,        // Links
    /```[\s\S]*```/,       // Code blocks
    /^\s*>\s+/m,           // Blockquotes
    /\*\*.+\*\*/,          // Bold
    /\*.+\*/,              // Italic
    /\|.+\|/m              // Tables
  ];

  return markdownPatterns.some(pattern => pattern.test(content));
}

export function MarkdownRenderer({
  content,
  className,
  defaultView = 'rendered',
  showToggle = true
}: MarkdownRendererProps) {
  const [view, setView] = useState<'raw' | 'rendered'>(defaultView);

  // Toggle button
  const toggleButton = showToggle ? (
    <div className="flex items-center justify-end mb-2">
      <div className="inline-flex rounded-md border border-input bg-background p-0.5">
        <Button
          variant={view === 'rendered' ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2"
          onClick={() => setView('rendered')}
        >
          <FileText className="h-3.5 w-3.5 mr-1" />
          Rendered
        </Button>
        <Button
          variant={view === 'raw' ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2"
          onClick={() => setView('raw')}
        >
          <Code className="h-3.5 w-3.5 mr-1" />
          Raw
        </Button>
      </div>
    </div>
  ) : null;

  // Raw view
  if (view === 'raw') {
    return (
      <div className={cn('space-y-2', className)}>
        {toggleButton}
        <pre className="bg-muted p-4 rounded-md overflow-x-auto text-sm font-mono whitespace-pre-wrap break-words">
          {content}
        </pre>
      </div>
    );
  }

  // Rendered view
  return (
    <div className={cn('space-y-2', className)}>
      {toggleButton}
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // Custom code block rendering with syntax highlighting
            code({ node, className: codeClassName, children, ...props }) {
              const match = /language-(\w+)/.exec(codeClassName || '');
              const isInline = !match && !codeClassName;
              const codeContent = String(children).replace(/\n$/, '');

              if (isInline) {
                return (
                  <code
                    className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono"
                    {...props}
                  >
                    {children}
                  </code>
                );
              }

              const language = match ? match[1] : detectLanguage({ content: codeContent });

              return (
                <SyntaxHighlighter
                  code={codeContent}
                  language={language}
                  className="my-4"
                />
              );
            },
            // Custom heading with anchor links
            h1: ({ children }) => (
              <h1 className="text-2xl font-bold mt-6 mb-4 pb-2 border-b">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xl font-semibold mt-6 mb-3">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-lg font-semibold mt-4 mb-2">
                {children}
              </h3>
            ),
            // Custom table styling
            table: ({ children }) => (
              <div className="overflow-x-auto my-4">
                <table className="min-w-full border border-border rounded-md">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }) => (
              <th className="px-4 py-2 bg-muted border-b border-border text-left font-medium">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="px-4 py-2 border-b border-border">
                {children}
              </td>
            ),
            // Custom blockquote
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-primary/50 pl-4 py-1 my-4 italic text-muted-foreground">
                {children}
              </blockquote>
            ),
            // Custom link with external indicator
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline underline-offset-4 hover:no-underline"
              >
                {children}
              </a>
            ),
            // Custom list styling
            ul: ({ children }) => (
              <ul className="list-disc list-inside space-y-1 my-2">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-inside space-y-1 my-2">
                {children}
              </ol>
            ),
            // Custom image with responsive sizing
            img: ({ src, alt }) => (
              <img
                src={src}
                alt={alt || ''}
                className="max-w-full h-auto rounded-md my-4"
              />
            )
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

export default MarkdownRenderer;
