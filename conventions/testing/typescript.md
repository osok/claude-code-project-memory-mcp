# TypeScript Testing Conventions

## Test Structure

```
project/
├── src/
│   ├── services/
│   │   └── userService.ts
│   └── controllers/
│       └── userController.ts
├── tests/
│   ├── unit/
│   │   └── services/
│   │       └── userService.test.ts
│   ├── integration/
│   │   └── api/
│   │       └── users.test.ts
│   └── fixtures/
│       └── users.ts
└── vitest.config.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{module}.test.ts` | `userService.test.ts` |
| Test suite | `describe('{Module}')` | `describe('UserService')` |
| Test case | `it('should {behavior}')` | `it('should return user by id')` |
| Mock file | `__mocks__/{module}.ts` | `__mocks__/database.ts` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Test runner | Vitest | Fast, ESM native |
| Assertions | Vitest expect | Jest-compatible |
| Mocking | vi.mock / vi.fn | Built into Vitest |
| HTTP mocking | MSW | Mock Service Worker |
| E2E | Playwright | Cross-browser |
| Coverage | c8 (via Vitest) | V8 coverage |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npm test` |
| Watch mode | `npm test -- --watch` |
| Coverage | `npm test -- --coverage` |
| Single file | `npm test -- userService` |
| UI mode | `npm test -- --ui` |
| Update snapshots | `npm test -- -u` |

## Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['**/*.test.ts', '**/fixtures/**'],
    },
    setupFiles: ['./tests/setup.ts'],
  },
});
```

## Unit Test Structure

```typescript
// tests/unit/services/userService.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { UserService } from '@/services/userService';
import { UserRepository } from '@/repositories/userRepository';

describe('UserService', () => {
  let userService: UserService;
  let mockRepository: MockedObject<UserRepository>;

  beforeEach(() => {
    mockRepository = {
      findById: vi.fn(),
      save: vi.fn(),
      delete: vi.fn(),
    };
    userService = new UserService(mockRepository);
  });

  describe('getUserById', () => {
    it('should return user when found', async () => {
      const expectedUser = { id: '1', name: 'John', email: 'john@example.com' };
      mockRepository.findById.mockResolvedValue(expectedUser);

      const result = await userService.getUserById('1');

      expect(result).toEqual(expectedUser);
      expect(mockRepository.findById).toHaveBeenCalledWith('1');
    });

    it('should throw NotFoundError when user not found', async () => {
      mockRepository.findById.mockResolvedValue(null);

      await expect(userService.getUserById('999'))
        .rejects.toThrow('User not found');
    });
  });
});
```

## Mocking

```typescript
// Module mocking
vi.mock('@/services/emailService', () => ({
  EmailService: vi.fn().mockImplementation(() => ({
    send: vi.fn().mockResolvedValue(true),
  })),
}));

// Function mocking
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Spy on method
const spy = vi.spyOn(userService, 'validateEmail');

// Mock implementation
mockRepository.findById.mockImplementation(async (id) => {
  if (id === '1') return { id: '1', name: 'John' };
  return null;
});
```

## API Mocking with MSW

```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/users/:id', ({ params }) => {
    if (params.id === '999') {
      return new HttpResponse(null, { status: 404 });
    }
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

// tests/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

// tests/setup.ts
import { beforeAll, afterAll, afterEach } from 'vitest';
import { server } from './mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterAll(() => server.close());
afterEach(() => server.resetHandlers());
```

## Integration Tests

```typescript
// tests/integration/api/users.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createApp } from '@/app';
import { createTestDatabase, cleanupDatabase } from '../helpers/database';

describe('Users API', () => {
  let app: FastifyInstance;
  let db: TestDatabase;

  beforeAll(async () => {
    db = await createTestDatabase();
    app = createApp({ database: db });
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
    await cleanupDatabase(db);
  });

  describe('POST /users', () => {
    it('should create a user', async () => {
      const response = await app.inject({
        method: 'POST',
        url: '/users',
        payload: { name: 'John', email: 'john@example.com' },
      });

      expect(response.statusCode).toBe(201);
      expect(response.json()).toMatchObject({
        name: 'John',
        email: 'john@example.com',
      });
    });

    it('should return 400 for invalid email', async () => {
      const response = await app.inject({
        method: 'POST',
        url: '/users',
        payload: { name: 'John', email: 'invalid' },
      });

      expect(response.statusCode).toBe(400);
    });
  });
});
```

## Test Fixtures

```typescript
// tests/fixtures/users.ts
import { User } from '@/models/user';

export function createTestUser(overrides: Partial<User> = {}): User {
  return {
    id: '1',
    name: 'Test User',
    email: 'test@example.com',
    createdAt: new Date('2024-01-01'),
    ...overrides,
  };
}

export function createTestUsers(count: number): User[] {
  return Array.from({ length: count }, (_, i) =>
    createTestUser({ id: String(i + 1), name: `User ${i + 1}` })
  );
}
```

## Type-Safe Mocks

```typescript
import { MockedFunction, MockedObject } from 'vitest';

// Type-safe mock function
type UserRepository = {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<User>;
};

const mockRepo: MockedObject<UserRepository> = {
  findById: vi.fn(),
  save: vi.fn(),
};

// Properly typed mock
mockRepo.findById.mockResolvedValue(createTestUser());
```

## Coverage Target

- Minimum: 70% line coverage
- Focus on business logic and error paths
- Exclude types, constants, generated code
