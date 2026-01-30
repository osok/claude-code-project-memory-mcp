# Svelte Testing Conventions

## Test Structure

```
tests/
├── unit/
│   ├── components/
│   │   └── UserProfile.test.ts
│   ├── stores/
│   │   └── userStore.test.ts
│   └── utils/
│       └── formatters.test.ts
├── integration/
│   └── routes/
│       └── users.test.ts
└── e2e/
    └── auth.test.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{Component}.test.ts` | `UserProfile.test.ts` |
| Test suite | `describe('{Component}')` | `describe('UserProfile')` |
| Test case | Describes behavior | `it('displays user name')` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Unit tests | Vitest | Fast, Vite-native |
| Component testing | Testing Library | @testing-library/svelte |
| E2E | Playwright | Cross-browser |
| Coverage | c8 | Via Vitest |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npm run test` |
| Watch | `npm run test:watch` |
| Coverage | `npm run test:coverage` |
| E2E | `npm run test:e2e` |

## Component Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import UserProfile from '$lib/components/UserProfile.svelte';

describe('UserProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays loading state initially', () => {
    render(UserProfile, { props: { userId: '123' } });

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('displays user name after loading', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '123', name: 'Test User' })
    });

    render(UserProfile, { props: { userId: '123' } });

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
  });

  it('displays error message on fetch failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    render(UserProfile, { props: { userId: '123' } });

    await waitFor(() => {
      expect(screen.getByText('Failed to load user')).toBeInTheDocument();
    });
  });

  it('calls ondelete when delete button clicked', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '123', name: 'Test User' })
    });

    const ondelete = vi.fn();
    render(UserProfile, { props: { userId: '123', ondelete } });

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    await fireEvent.click(screen.getByText('Delete'));

    expect(ondelete).toHaveBeenCalledOnce();
  });

  it('shows details when showDetails is true', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '123', name: 'Test User' })
    });

    render(UserProfile, { props: { userId: '123', showDetails: true } });

    await waitFor(() => {
      expect(screen.getByTestId('user-details')).toBeInTheDocument();
    });
  });
});
```

## Store Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { userStore, isAuthenticated } from '$lib/stores/userStore';

describe('userStore', () => {
  beforeEach(() => {
    userStore.clear();
    vi.clearAllMocks();
  });

  it('starts with null user', () => {
    expect(get(userStore)).toBeNull();
    expect(get(isAuthenticated)).toBe(false);
  });

  it('fetches and sets user', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '123', name: 'Test User' })
    });

    await userStore.fetch('123');

    expect(get(userStore)).toEqual({ id: '123', name: 'Test User' });
    expect(get(isAuthenticated)).toBe(true);
  });

  it('clears user', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '123', name: 'Test User' })
    });

    await userStore.fetch('123');
    userStore.clear();

    expect(get(userStore)).toBeNull();
  });
});
```

## Server Load Function Tests

```typescript
import { describe, it, expect, vi } from 'vitest';
import { load } from './+page.server';

describe('+page.server load', () => {
  it('returns user data', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '123', name: 'Test User' })
    });

    const result = await load({
      params: { id: '123' },
      fetch: mockFetch
    } as any);

    expect(result.user).toEqual({ id: '123', name: 'Test User' });
  });

  it('throws 404 error when user not found', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404
    });

    await expect(load({
      params: { id: 'non-existent' },
      fetch: mockFetch
    } as any)).rejects.toMatchObject({
      status: 404
    });
  });
});
```

## E2E Tests (Playwright)

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Profile', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('/api/users/*', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ id: '123', name: 'Test User' })
      });
    });
  });

  test('displays user profile', async ({ page }) => {
    await page.goto('/users/123');

    await expect(page.locator('h1')).toContainText('Test User');
  });

  test('navigates to edit page', async ({ page }) => {
    await page.goto('/users/123');

    await page.click('text=Edit');

    await expect(page).toHaveURL('/users/123/edit');
  });

  test('handles delete action', async ({ page }) => {
    await page.route('/api/users/123', route => {
      if (route.request().method() === 'DELETE') {
        route.fulfill({ status: 204 });
      }
    });

    await page.goto('/users/123');
    await page.click('text=Delete');

    // Confirm dialog
    await page.click('text=Confirm');

    await expect(page).toHaveURL('/users');
  });
});
```

## Testing Utilities

```typescript
// tests/utils.ts
import { render } from '@testing-library/svelte';
import type { ComponentProps, SvelteComponent } from 'svelte';

export function renderWithFetch<T extends SvelteComponent>(
  Component: new (...args: any[]) => T,
  props: ComponentProps<T>,
  fetchMock: jest.Mock
) {
  global.fetch = fetchMock;
  return render(Component, { props });
}
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on stores and component logic
- Test user interactions over implementation
