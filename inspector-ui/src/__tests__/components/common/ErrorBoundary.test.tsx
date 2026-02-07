/**
 * ErrorBoundary Component Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary, InlineError, NetworkError } from '@/components/common/ErrorBoundary';

// Suppress console.error for error boundary tests
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalConsoleError;
});

// Component that throws an error
function ThrowingComponent(): JSX.Element {
  throw new Error('Test error');
}

// Component that renders normally
function NormalComponent(): JSX.Element {
  return <div>Normal content</div>;
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <NormalComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Normal content')).toBeTruthy();
  });

  it('renders error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeTruthy();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom error UI</div>}>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error UI')).toBeTruthy();
  });

  it('shows reload button in error state', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Reload Page')).toBeTruthy();
  });
});

describe('InlineError', () => {
  it('renders default message', () => {
    render(<InlineError />);

    expect(screen.getByText('Failed to load')).toBeTruthy();
  });

  it('renders custom message', () => {
    render(<InlineError message="Custom error message" />);

    expect(screen.getByText('Custom error message')).toBeTruthy();
  });

  it('renders error details when error provided', () => {
    const error = new Error('Detailed error');
    render(<InlineError error={error} />);

    expect(screen.getByText('Detailed error')).toBeTruthy();
  });

  it('shows retry button when onRetry provided', () => {
    const mockRetry = vi.fn();
    render(<InlineError onRetry={mockRetry} />);

    const retryButton = screen.getByText('Retry');
    expect(retryButton).toBeTruthy();

    fireEvent.click(retryButton);
    expect(mockRetry).toHaveBeenCalled();
  });
});

describe('NetworkError', () => {
  it('renders network error message', () => {
    render(<NetworkError />);

    expect(screen.getByText('Connection Error')).toBeTruthy();
  });

  it('shows try again button when onRetry provided', () => {
    const mockRetry = vi.fn();
    render(<NetworkError onRetry={mockRetry} />);

    const retryButton = screen.getByText('Try Again');
    fireEvent.click(retryButton);

    expect(mockRetry).toHaveBeenCalled();
  });
});
