# Next.js Testing Conventions

## Test Structure

```
__tests__/
├── unit/
│   ├── components/
│   │   └── UserForm.test.tsx
│   ├── lib/
│   │   └── utils.test.ts
│   └── hooks/
│       └── useUser.test.ts
├── integration/
│   ├── api/
│   │   └── users.test.ts
│   └── actions/
│       └── createUser.test.ts
└── e2e/
    └── users.spec.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{Component}.test.tsx` | `UserForm.test.tsx` |
| API test | `{route}.test.ts` | `users.test.ts` |
| E2E test | `{feature}.spec.ts` | `users.spec.ts` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Unit tests | Jest + React Testing Library | Standard |
| API testing | Jest + node-mocks-http | API routes |
| E2E | Playwright | Cross-browser |
| Mocking | MSW | API mocking |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npm run test` |
| Watch | `npm run test:watch` |
| Coverage | `npm run test:coverage` |
| E2E | `npm run test:e2e` |

## Client Component Tests

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserForm } from '@/components/features/UserForm';
import { createUser } from '@/lib/actions/users';

jest.mock('@/lib/actions/users');

describe('UserForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders form fields', () => {
    render(<UserForm />);

    expect(screen.getByPlaceholderText('Name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
  });

  it('shows validation errors', async () => {
    const user = userEvent.setup();
    render(<UserForm />);

    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    });
  });

  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    (createUser as jest.Mock).mockResolvedValue({});

    render(<UserForm />);

    await user.type(screen.getByPlaceholderText('Name'), 'Test User');
    await user.type(screen.getByPlaceholderText('Email'), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(createUser).toHaveBeenCalledWith({
        name: 'Test User',
        email: 'test@example.com',
      });
    });
  });

  it('displays server error', async () => {
    const user = userEvent.setup();
    (createUser as jest.Mock).mockResolvedValue({ error: 'Email already exists' });

    render(<UserForm />);

    await user.type(screen.getByPlaceholderText('Name'), 'Test User');
    await user.type(screen.getByPlaceholderText('Email'), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText('Email already exists')).toBeInTheDocument();
    });
  });
});
```

## Server Component Tests

```tsx
import { render } from '@testing-library/react';
import UserPage from '@/app/users/[id]/page';
import { getUser } from '@/services/users';

jest.mock('@/services/users');
jest.mock('next/navigation', () => ({
  notFound: jest.fn(),
}));

describe('UserPage', () => {
  it('renders user details', async () => {
    (getUser as jest.Mock).mockResolvedValue({
      id: '123',
      name: 'Test User',
      email: 'test@example.com',
    });

    const page = await UserPage({ params: { id: '123' } });
    const { getByText } = render(page);

    expect(getByText('Test User')).toBeInTheDocument();
  });

  it('calls notFound when user does not exist', async () => {
    const { notFound } = require('next/navigation');
    (getUser as jest.Mock).mockResolvedValue(null);

    await UserPage({ params: { id: 'non-existent' } });

    expect(notFound).toHaveBeenCalled();
  });
});
```

## API Route Tests

```typescript
import { GET, POST } from '@/app/api/users/route';
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';

jest.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findMany: jest.fn(),
      create: jest.fn(),
    },
  },
}));

describe('/api/users', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('GET', () => {
    it('returns paginated users', async () => {
      const mockUsers = [{ id: '1', name: 'Test' }];
      (prisma.user.findMany as jest.Mock).mockResolvedValue(mockUsers);

      const request = new NextRequest('http://localhost/api/users?page=1');
      const response = await GET(request);
      const data = await response.json();

      expect(data).toEqual(mockUsers);
      expect(prisma.user.findMany).toHaveBeenCalledWith({
        skip: 0,
        take: 10,
      });
    });
  });

  describe('POST', () => {
    it('creates a new user', async () => {
      const newUser = { id: '1', name: 'Test', email: 'test@example.com' };
      (prisma.user.create as jest.Mock).mockResolvedValue(newUser);

      const request = new NextRequest('http://localhost/api/users', {
        method: 'POST',
        body: JSON.stringify({ name: 'Test', email: 'test@example.com' }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data).toEqual(newUser);
    });
  });
});
```

## Server Action Tests

```typescript
import { createUser } from '@/lib/actions/users';
import { prisma } from '@/lib/prisma';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';

jest.mock('@/lib/prisma');
jest.mock('next/cache');
jest.mock('next/navigation');

describe('createUser action', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('creates user and redirects', async () => {
    (prisma.user.create as jest.Mock).mockResolvedValue({
      id: '1',
      name: 'Test',
    });

    await createUser({ name: 'Test', email: 'test@example.com' });

    expect(prisma.user.create).toHaveBeenCalled();
    expect(revalidatePath).toHaveBeenCalledWith('/users');
    expect(redirect).toHaveBeenCalledWith('/users');
  });

  it('returns error for invalid data', async () => {
    const result = await createUser({ name: '', email: 'invalid' });

    expect(result).toEqual({ error: 'Invalid data' });
    expect(prisma.user.create).not.toHaveBeenCalled();
  });
});
```

## E2E Tests (Playwright)

```typescript
import { test, expect } from '@playwright/test';

test.describe('Users', () => {
  test('creates a new user', async ({ page }) => {
    await page.goto('/users/new');

    await page.fill('input[placeholder="Name"]', 'New User');
    await page.fill('input[placeholder="Email"]', 'new@example.com');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/users');
    await expect(page.locator('text=New User')).toBeVisible();
  });

  test('views user details', async ({ page }) => {
    await page.goto('/users');
    await page.click('text=Test User');

    await expect(page.locator('h1')).toContainText('Test User');
  });
});
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on Server Actions, API routes, and client components
- Use MSW for API mocking in tests
