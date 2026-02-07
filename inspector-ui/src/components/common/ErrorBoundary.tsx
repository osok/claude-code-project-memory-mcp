/**
 * Error Boundary Component
 *
 * Catches React errors and displays a fallback UI.
 */
import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    // Log to console in development
    console.error('Error caught by boundary:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    this.props.onReset?.();
  };

  handleGoHome = () => {
    window.location.href = '/browser';
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-destructive/10 mb-4">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>

          <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
          <p className="text-muted-foreground text-center max-w-md mb-6">
            An unexpected error occurred. This might be a temporary issue.
          </p>

          {/* Error details (collapsed by default) */}
          {this.state.error && (
            <details className="mb-6 w-full max-w-lg">
              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                View error details
              </summary>
              <div className="mt-2 p-3 bg-muted rounded-md overflow-auto max-h-48">
                <p className="font-mono text-xs text-destructive break-all">
                  {this.state.error.message}
                </p>
                {this.state.error.stack && (
                  <pre className="mt-2 font-mono text-[10px] text-muted-foreground whitespace-pre-wrap">
                    {this.state.error.stack}
                  </pre>
                )}
              </div>
            </details>
          )}

          <div className="flex gap-3">
            <Button variant="outline" onClick={this.handleGoHome}>
              <Home className="h-4 w-4 mr-2" />
              Go Home
            </Button>
            <Button onClick={this.handleReload}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reload Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Error fallback for inline/smaller components
 */
interface InlineErrorProps {
  error?: Error | null;
  message?: string;
  onRetry?: () => void;
}

export function InlineError({ error, message, onRetry }: InlineErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center p-6 text-center">
      <AlertTriangle className="h-6 w-6 text-destructive mb-2" />
      <p className="text-sm text-destructive font-medium">
        {message || 'Failed to load'}
      </p>
      {error && (
        <p className="text-xs text-muted-foreground mt-1">
          {error.message}
        </p>
      )}
      {onRetry && (
        <Button variant="ghost" size="sm" onClick={onRetry} className="mt-3">
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      )}
    </div>
  );
}

/**
 * Network error component
 */
interface NetworkErrorProps {
  onRetry?: () => void;
}

export function NetworkError({ onRetry }: NetworkErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-amber-500/10 mb-4">
        <AlertTriangle className="h-6 w-6 text-amber-500" />
      </div>
      <h3 className="font-medium mb-1">Connection Error</h3>
      <p className="text-sm text-muted-foreground mb-4">
        Unable to connect to the server. Please check your connection.
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      )}
    </div>
  );
}

export default ErrorBoundary;
