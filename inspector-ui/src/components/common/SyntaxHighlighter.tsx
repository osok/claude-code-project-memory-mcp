/**
 * Syntax Highlighter Component
 *
 * Language-aware syntax highlighting using Prism.js.
 * Supports theme switching (light/dark) and language detection.
 * REQ-007-FN-011: Syntax highlighting with language detection
 */
import { useEffect, useMemo } from 'react';
import Prism from 'prismjs';

// Import core languages
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-jsx';
import 'prismjs/components/prism-tsx';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-markup'; // HTML
import 'prismjs/components/prism-markdown';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-csharp';

import { cn } from '@/lib/utils';

// Language aliases for detection
const LANGUAGE_ALIASES: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  yml: 'yaml',
  html: 'markup',
  htm: 'markup',
  md: 'markdown',
  cs: 'csharp'
};

// File extension to language mapping
const EXTENSION_TO_LANGUAGE: Record<string, string> = {
  '.js': 'javascript',
  '.mjs': 'javascript',
  '.jsx': 'jsx',
  '.ts': 'typescript',
  '.tsx': 'tsx',
  '.py': 'python',
  '.json': 'json',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.sql': 'sql',
  '.sh': 'bash',
  '.bash': 'bash',
  '.css': 'css',
  '.html': 'markup',
  '.htm': 'markup',
  '.md': 'markdown',
  '.go': 'go',
  '.rs': 'rust',
  '.java': 'java',
  '.cs': 'csharp'
};

interface SyntaxHighlighterProps {
  code: string;
  language?: string;
  filePath?: string;
  className?: string;
  showLineNumbers?: boolean;
}

/**
 * Detects language from metadata, file path, or content analysis.
 */
export function detectLanguage(options: {
  language?: string;
  filePath?: string;
  content?: string;
}): string {
  const { language, filePath, content } = options;

  // 1. Use explicit language if provided
  if (language) {
    const normalized = language.toLowerCase();
    return LANGUAGE_ALIASES[normalized] || normalized;
  }

  // 2. Detect from file extension
  if (filePath) {
    const ext = filePath.slice(filePath.lastIndexOf('.')).toLowerCase();
    const lang = EXTENSION_TO_LANGUAGE[ext];
    if (lang) return lang;
  }

  // 3. Try to detect from content
  if (content) {
    // Check for shebang
    if (content.startsWith('#!/usr/bin/env python') || content.startsWith('#!/usr/bin/python')) {
      return 'python';
    }
    if (content.startsWith('#!/bin/bash') || content.startsWith('#!/bin/sh')) {
      return 'bash';
    }

    // Check for common patterns
    if (content.includes('function ') && (content.includes('const ') || content.includes('let '))) {
      return 'javascript';
    }
    if (content.includes('interface ') && content.includes(': ')) {
      return 'typescript';
    }
    if (content.includes('def ') && content.includes(':')) {
      return 'python';
    }
    if (content.trim().startsWith('{') && content.includes('":')) {
      return 'json';
    }
    if (content.includes('SELECT ') || content.includes('INSERT ') || content.includes('CREATE TABLE')) {
      return 'sql';
    }
  }

  // Default to plain text
  return 'plaintext';
}

export function SyntaxHighlighter({
  code,
  language,
  filePath,
  className,
  showLineNumbers = false
}: SyntaxHighlighterProps) {
  // Detect language
  const detectedLanguage = detectLanguage({ language, filePath, content: code });
  const prismLanguage = Prism.languages[detectedLanguage] ? detectedLanguage : 'plaintext';

  // Highlight code and split into lines
  const highlightedLines = useMemo(() => {
    const grammar = Prism.languages[prismLanguage];
    if (!grammar) {
      return code.split('\n').map(line => line || ' '); // Keep empty lines visible
    }

    const highlighted = Prism.highlight(code, grammar, prismLanguage);
    // Split by newlines but preserve HTML tags
    return highlighted.split('\n').map(line => line || ' '); // Keep empty lines visible
  }, [code, prismLanguage]);

  return (
    <div className={cn('relative rounded-md bg-muted', className)}>
      {/* Language badge */}
      <div className="absolute top-2 right-2 text-xs text-muted-foreground bg-background/80 px-2 py-0.5 rounded z-10">
        {detectedLanguage}
      </div>

      {/* Code container with horizontal scroll */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm font-mono">
          <tbody>
            {highlightedLines.map((line, index) => (
              <tr key={index} className="hover:bg-muted-foreground/5">
                {showLineNumbers && (
                  <td className="select-none text-right text-muted-foreground/60 pr-4 pl-4 py-0 align-top border-r border-border/50 bg-muted/50 sticky left-0">
                    <span className="text-xs">{index + 1}</span>
                  </td>
                )}
                <td className="pl-4 pr-4 py-0 whitespace-pre">
                  <span
                    dangerouslySetInnerHTML={{ __html: line }}
                    className={`language-${prismLanguage}`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default SyntaxHighlighter;
