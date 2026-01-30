# Vue Testing Conventions

## Test Structure

```
tests/
├── unit/
│   ├── components/
│   │   └── UserProfile.spec.ts
│   ├── composables/
│   │   └── useAuth.spec.ts
│   └── stores/
│       └── user.spec.ts
├── integration/
│   └── UserFlow.spec.ts
└── e2e/
    └── auth.spec.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{Component}.spec.ts` | `UserProfile.spec.ts` |
| Test suite | Describe component | `describe('UserProfile')` |
| Test case | Describes behavior | `it('displays user name')` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Unit tests | Vitest | Fast, Vite-native |
| Component testing | Vue Test Utils | Official |
| Mocking | vi (Vitest) | Built-in |
| E2E | Playwright | Cross-browser |
| Coverage | c8 | Via Vitest |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npm run test` |
| Watch mode | `npm run test:watch` |
| Coverage | `npm run test:coverage` |
| UI mode | `npm run test:ui` |
| E2E | `npm run test:e2e` |

## Component Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import UserProfile from '@/components/UserProfile.vue'
import { useUserStore } from '@/stores/user'

describe('UserProfile', () => {
  const mountComponent = (props = {}) => {
    return mount(UserProfile, {
      props: {
        userId: '123',
        ...props,
      },
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
          }),
        ],
      },
    })
  }

  it('displays user name from store', async () => {
    const wrapper = mountComponent()
    const store = useUserStore()

    store.currentUser = { id: '123', name: 'Test User' }
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Test User')
  })

  it('shows loading state', () => {
    const wrapper = mountComponent()

    expect(wrapper.find('[data-test="loading"]').exists()).toBe(true)
  })

  it('emits delete event when button clicked', async () => {
    const wrapper = mountComponent()
    const store = useUserStore()
    store.currentUser = { id: '123', name: 'Test' }
    await wrapper.vm.$nextTick()

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('delete')).toBeTruthy()
  })

  it('renders details when showDetails is true', async () => {
    const wrapper = mountComponent({ showDetails: true })
    const store = useUserStore()
    store.currentUser = { id: '123', name: 'Test' }
    await wrapper.vm.$nextTick()

    expect(wrapper.findComponent({ name: 'UserDetails' }).exists()).toBe(true)
  })
})
```

## Composable Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuth } from '@/composables/useAuth'
import { authService } from '@/services/auth'

vi.mock('@/services/auth')
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

describe('useAuth', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts with no user', () => {
    const { user, isAuthenticated } = useAuth()

    expect(user.value).toBeNull()
    expect(isAuthenticated.value).toBe(false)
  })

  it('logs in user successfully', async () => {
    const mockUser = { id: '1', name: 'Test' }
    vi.mocked(authService.login).mockResolvedValue(mockUser)

    const { login, user, isAuthenticated } = useAuth()
    await login('test@example.com', 'password')

    expect(user.value).toEqual(mockUser)
    expect(isAuthenticated.value).toBe(true)
  })

  it('clears user on logout', async () => {
    const { login, logout, user } = useAuth()

    vi.mocked(authService.login).mockResolvedValue({ id: '1', name: 'Test' })
    await login('test@example.com', 'password')

    await logout()

    expect(user.value).toBeNull()
  })
})
```

## Store Tests

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import { userService } from '@/services/user'

vi.mock('@/services/user')

describe('userStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches user and updates state', async () => {
    const mockUser = { id: '123', name: 'Test User' }
    vi.mocked(userService.getUser).mockResolvedValue(mockUser)

    const store = useUserStore()
    await store.fetchUser('123')

    expect(store.currentUser).toEqual(mockUser)
    expect(store.isLoading).toBe(false)
  })

  it('handles fetch error', async () => {
    vi.mocked(userService.getUser).mockRejectedValue(new Error('Failed'))

    const store = useUserStore()
    await store.fetchUser('123')

    expect(store.error).toBe('Failed to fetch user')
    expect(store.currentUser).toBeNull()
  })
})
```

## E2E Tests (Playwright)

```typescript
import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('user can login', async ({ page }) => {
    await page.goto('/login')

    await page.fill('[data-test="email"]', 'test@example.com')
    await page.fill('[data-test="password"]', 'password123')
    await page.click('[data-test="submit"]')

    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('[data-test="welcome"]')).toContainText('Welcome')
  })

  test('shows error for invalid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('[data-test="email"]', 'wrong@example.com')
    await page.fill('[data-test="password"]', 'wrong')
    await page.click('[data-test="submit"]')

    await expect(page.locator('[data-test="error"]')).toBeVisible()
  })
})
```

## Testing Utilities

```typescript
// tests/utils.ts
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { vi } from 'vitest'

export function createWrapper(component: any, options = {}) {
  return mount(component, {
    global: {
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          stubActions: false,
        }),
      ],
      stubs: {
        RouterLink: true,
        RouterView: true,
      },
    },
    ...options,
  })
}
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on composables and store logic
- Test component interactions, not implementation
