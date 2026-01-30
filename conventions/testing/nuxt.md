# Nuxt Testing Conventions

## Test Structure

```
tests/
├── unit/
│   ├── components/
│   │   └── UserProfile.test.ts
│   ├── composables/
│   │   └── useAuth.test.ts
│   └── stores/
│       └── user.test.ts
├── integration/
│   └── api/
│       └── users.test.ts
└── e2e/
    └── users.spec.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{Component}.test.ts` | `UserProfile.test.ts` |
| Test suite | `describe('{Component}')` | `describe('UserProfile')` |
| Test case | Descriptive behavior | `it('displays user name')` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Unit tests | Vitest | Fast, Vite-native |
| Component testing | @nuxt/test-utils | Nuxt-specific |
| Mocking | vi (Vitest) | Built-in |
| E2E | Playwright | Cross-browser |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npm run test` |
| Watch | `npm run test:watch` |
| Coverage | `npm run test:coverage` |
| E2E | `npm run test:e2e` |

## Component Tests

```typescript
import { describe, it, expect, vi } from 'vitest';
import { mountSuspended } from '@nuxt/test-utils/runtime';
import UserProfile from '~/components/UserProfile.vue';

describe('UserProfile', () => {
  it('displays user name', async () => {
    const wrapper = await mountSuspended(UserProfile, {
      props: {
        user: { id: '123', name: 'Test User', email: 'test@example.com' },
      },
    });

    expect(wrapper.text()).toContain('Test User');
  });

  it('emits delete event when button clicked', async () => {
    const wrapper = await mountSuspended(UserProfile, {
      props: {
        user: { id: '123', name: 'Test User' },
      },
    });

    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('delete')).toBeTruthy();
  });

  it('shows details when expanded', async () => {
    const wrapper = await mountSuspended(UserProfile, {
      props: {
        user: { id: '123', name: 'Test User', email: 'test@example.com' },
        showDetails: true,
      },
    });

    expect(wrapper.find('[data-test="user-details"]').exists()).toBe(true);
  });
});
```

## Composable Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuth } from '~/composables/useAuth';

// Mock Nuxt composables
vi.mock('#app', () => ({
  useState: vi.fn((key, init) => ref(init?.())),
  navigateTo: vi.fn(),
  useFetch: vi.fn(),
}));

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts with no user', () => {
    const { user, isAuthenticated } = useAuth();

    expect(user.value).toBeNull();
    expect(isAuthenticated.value).toBe(false);
  });

  it('logs in user', async () => {
    const mockUser = { id: '1', name: 'Test' };
    const { useFetch, navigateTo } = await import('#app');

    vi.mocked(useFetch).mockResolvedValue({ data: ref(mockUser) });

    const { login, user } = useAuth();
    await login('test@example.com', 'password');

    expect(user.value).toEqual(mockUser);
    expect(navigateTo).toHaveBeenCalledWith('/dashboard');
  });
});
```

## API Route Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createEvent } from 'h3';

// Import the handler
import handler from '~/server/api/users/index';

// Mock Prisma
vi.mock('~/server/utils/prisma', () => ({
  prisma: {
    user: {
      findMany: vi.fn(),
      create: vi.fn(),
    },
  },
}));

describe('/api/users', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns paginated users', async () => {
    const { prisma } = await import('~/server/utils/prisma');
    const mockUsers = [{ id: '1', name: 'Test' }];

    vi.mocked(prisma.user.findMany).mockResolvedValue(mockUsers);

    const event = createEvent({
      method: 'GET',
      path: '/api/users',
      query: { page: '1' },
    });

    const result = await handler(event);

    expect(result).toEqual(mockUsers);
    expect(prisma.user.findMany).toHaveBeenCalledWith({
      skip: 0,
      take: 10,
    });
  });
});

// Test POST handler
import postHandler from '~/server/api/users/index.post';

describe('POST /api/users', () => {
  it('creates user with valid data', async () => {
    const { prisma } = await import('~/server/utils/prisma');
    const newUser = { id: '1', name: 'Test', email: 'test@example.com' };

    vi.mocked(prisma.user.create).mockResolvedValue(newUser);

    const event = createEvent({
      method: 'POST',
      path: '/api/users',
      body: { name: 'Test', email: 'test@example.com' },
    });

    const result = await postHandler(event);

    expect(result).toEqual(newUser);
  });

  it('throws error for invalid data', async () => {
    const event = createEvent({
      method: 'POST',
      path: '/api/users',
      body: { name: '', email: 'invalid' },
    });

    await expect(postHandler(event)).rejects.toThrow();
  });
});
```

## Store Tests

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useUserStore } from '~/stores/user';

describe('userStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('fetches and sets user', async () => {
    const store = useUserStore();

    // Mock the fetch
    global.$fetch = vi.fn().mockResolvedValue({ id: '1', name: 'Test' });

    await store.fetchUser('1');

    expect(store.user).toEqual({ id: '1', name: 'Test' });
  });

  it('clears user on logout', () => {
    const store = useUserStore();
    store.user = { id: '1', name: 'Test' };

    store.clear();

    expect(store.user).toBeNull();
  });
});
```

## E2E Tests (Playwright)

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-test="email"]', 'test@example.com');
    await page.fill('[data-test="password"]', 'password');
    await page.click('[data-test="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('displays user list', async ({ page }) => {
    await page.goto('/users');

    await expect(page.locator('[data-test="user-list"]')).toBeVisible();
    await expect(page.locator('[data-test="user-item"]')).toHaveCount(10);
  });

  test('creates new user', async ({ page }) => {
    await page.goto('/users/new');

    await page.fill('[data-test="name"]', 'New User');
    await page.fill('[data-test="email"]', 'new@example.com');
    await page.click('[data-test="submit"]');

    await expect(page).toHaveURL('/users');
    await expect(page.locator('text=New User')).toBeVisible();
  });

  test('views user details', async ({ page }) => {
    await page.goto('/users');
    await page.click('[data-test="user-item"]:first-child');

    await expect(page.locator('[data-test="user-details"]')).toBeVisible();
  });
});
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on composables, stores, and API routes
- Use @nuxt/test-utils for component testing
