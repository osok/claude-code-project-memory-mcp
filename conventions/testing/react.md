# React Testing Conventions

## Test Structure

```
src/
├── components/
│   └── UserProfile/
│       ├── UserProfile.tsx
│       ├── UserProfile.test.tsx    # Unit tests
│       └── UserProfile.stories.tsx # Storybook (optional)
├── hooks/
│   └── useAuth/
│       ├── useAuth.ts
│       └── useAuth.test.ts
├── __tests__/                      # Integration tests
│   └── flows/
└── e2e/                            # Playwright/Cypress tests
    └── user-flow.spec.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{Component}.test.tsx` | `UserProfile.test.tsx` |
| Test suite | `describe('{Component}')` | `describe('UserProfile')` |
| Test case | `it('should {behavior}')` | `it('should display user name')` |
| Mock file | `__mocks__/{module}.ts` | `__mocks__/api.ts` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Test runner | Vitest | Fast, ESM native |
| Component testing | React Testing Library | User-centric testing |
| E2E | Playwright | Cross-browser |
| Mocking | vi.mock / MSW | MSW for API mocking |
| Assertions | Vitest expect | Jest-compatible |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npm test` |
| Watch mode | `npm test -- --watch` |
| Coverage | `npm test -- --coverage` |
| Single file | `npm test -- UserProfile` |
| E2E | `npx playwright test` |
| E2E UI | `npx playwright test --ui` |

## Component Testing

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { UserProfile } from './UserProfile';

describe('UserProfile', () => {
  const defaultProps = {
    user: { id: '1', name: 'John Doe', email: 'john@example.com' },
    onEdit: vi.fn(),
  };

  it('should display user name', () => {
    render(<UserProfile {...defaultProps} />);

    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('should call onEdit when edit button clicked', async () => {
    render(<UserProfile {...defaultProps} />);

    await fireEvent.click(screen.getByRole('button', { name: /edit/i }));

    expect(defaultProps.onEdit).toHaveBeenCalledWith('1');
  });

  it('should display loading state', () => {
    render(<UserProfile {...defaultProps} isLoading />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});
```

## Hook Testing

```tsx
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from './useAuth';

describe('useAuth', () => {
  it('should return user after login', async () => {
    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.login('user@example.com', 'password');
    });

    await waitFor(() => {
      expect(result.current.user).toEqual({ email: 'user@example.com' });
    });
  });
});
```

## API Mocking with MSW

```tsx
// mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Test User',
    });
  }),

  http.post('/api/users', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: '1', ...body }, { status: 201 });
  }),
];

// mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// vitest.setup.ts
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## E2E Testing with Playwright

```typescript
// e2e/user-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('User Profile Flow', () => {
  test('should allow user to update profile', async ({ page }) => {
    // Navigate
    await page.goto('/profile');

    // Edit
    await page.click('button:has-text("Edit")');
    await page.fill('input[name="name"]', 'New Name');
    await page.click('button:has-text("Save")');

    // Verify
    await expect(page.getByText('New Name')).toBeVisible();
  });
});
```

## Test Utilities

```tsx
// test-utils.tsx
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

export function renderWithProviders(
  ui: React.ReactElement,
  options?: RenderOptions
) {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
    options
  );
}
```

## Accessibility Testing

```tsx
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('should have no accessibility violations', async () => {
  const { container } = render(<UserProfile {...defaultProps} />);
  const results = await axe(container);

  expect(results).toHaveNoViolations();
});
```

## Coverage Target

- Minimum: 70% line coverage
- Focus on user interactions and business logic
- Skip styling-only tests
