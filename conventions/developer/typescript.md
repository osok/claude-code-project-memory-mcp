# TypeScript Conventions

## Project Structure

```
project/
├── src/
│   ├── index.ts              # Entry point
│   ├── config/               # Configuration
│   ├── controllers/          # Request handlers
│   ├── services/             # Business logic
│   ├── repositories/         # Data access
│   ├── models/               # Data models
│   ├── types/                # Type definitions
│   ├── middleware/           # Express/Fastify middleware
│   ├── utils/                # Utilities
│   └── routes/               # Route definitions
├── tests/
│   ├── unit/
│   └── integration/
├── package.json
├── tsconfig.json
└── .env.example
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| File | camelCase or kebab-case | `userService.ts` or `user-service.ts` |
| Class | PascalCase | `UserService` |
| Interface | PascalCase (no I prefix) | `User`, `UserService` |
| Type | PascalCase | `UserId` |
| Function | camelCase | `getUserById` |
| Variable | camelCase | `userCount` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| Enum | PascalCase | `UserStatus` |
| Enum values | PascalCase | `UserStatus.Active` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Runtime | Node.js 20+ | LTS version |
| Framework | Fastify or Express | Fastify preferred |
| Validation | Zod | Runtime type validation |
| ORM | Prisma or Drizzle | Prisma for simplicity, Drizzle for performance |
| HTTP client | fetch or axios | Native fetch in Node 18+ |
| Logging | Pino | Fastify default |
| Testing | Vitest | Fast, ESM native |
| Linting | ESLint | With TypeScript plugin |
| Formatting | Prettier | Consistent style |

## Build Commands

| Action | Command |
|--------|---------|
| Dev | `npm run dev` |
| Build | `npm run build` |
| Start | `npm start` |
| Test | `npm test` |
| Lint | `npm run lint` |
| Format | `npm run format` |
| Type check | `tsc --noEmit` |

## TypeScript Config

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src"
  }
}
```

## Code Style

- Enable strict mode in tsconfig
- Prefer `type` over `interface` for object types
- Use `unknown` over `any`
- Prefer `const` over `let`
- Use nullish coalescing (`??`) and optional chaining (`?.`)
- Avoid type assertions (`as`) when possible
- Use discriminated unions for state

## Type Patterns

```typescript
// Result type for error handling
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

// Branded types for type safety
type UserId = string & { readonly brand: unique symbol };

// Zod schema with inferred type
const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1),
});
type User = z.infer<typeof UserSchema>;
```

## Error Handling

```typescript
// Custom errors
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500
  ) {
    super(message);
    this.name = 'AppError';
  }
}

class NotFoundError extends AppError {
  constructor(resource: string) {
    super(`${resource} not found`, 'NOT_FOUND', 404);
  }
}
```
