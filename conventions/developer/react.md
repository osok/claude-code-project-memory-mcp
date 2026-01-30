# React Conventions

## Project Structure

```
project/
├── src/
│   ├── components/
│   │   ├── common/        # Shared/reusable components
│   │   └── {feature}/     # Feature-specific components
│   ├── hooks/             # Custom hooks
│   ├── contexts/          # React contexts
│   ├── services/          # API calls, external services
│   ├── utils/             # Utility functions
│   ├── types/             # TypeScript types/interfaces
│   ├── styles/            # Global styles, themes
│   ├── assets/            # Images, fonts, static files
│   └── App.tsx
├── public/
├── package.json
└── tsconfig.json
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Component file | PascalCase | `UserProfile.tsx` |
| Component | PascalCase | `UserProfile` |
| Hook file | camelCase with use prefix | `useAuth.ts` |
| Hook | camelCase with use prefix | `useAuth` |
| Context | PascalCase with Context suffix | `AuthContext` |
| Utility file | camelCase | `formatDate.ts` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| Props interface | PascalCase with Props suffix | `UserProfileProps` |

## Component Structure

```tsx
// Imports (external, then internal)
import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';

// Types
interface ComponentProps {
  // props definition
}

// Component
export function Component({ prop1, prop2 }: ComponentProps) {
  // hooks first
  // state
  // effects
  // handlers
  // render
}
```

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| State management | Zustand or React Query | Zustand for client state, React Query for server state |
| Routing | React Router | v6+ |
| Forms | React Hook Form | With zod for validation |
| Styling | Tailwind CSS or styled-components | Tailwind preferred |
| HTTP client | Axios or fetch | With React Query |
| Icons | Lucide React | Consistent icon set |
| Date handling | date-fns | Tree-shakeable |
| UI components | Radix UI or shadcn/ui | Accessible primitives |

## Build Commands

| Action | Command |
|--------|---------|
| Dev server | `npm run dev` |
| Build | `npm run build` |
| Preview | `npm run preview` |
| Lint | `npm run lint` |
| Format | `npm run format` or `prettier --write .` |
| Type check | `tsc --noEmit` |

## Code Style

- Prefer functional components over class components
- Use TypeScript strict mode
- Colocate related files (component, styles, tests)
- Keep components small and focused
- Extract logic to custom hooks
- Use absolute imports with `@/` prefix
- Memoize expensive computations with useMemo
- Memoize callbacks passed to children with useCallback

## Theme/UI Consistency

- Define theme tokens (colors, spacing, typography) in one place
- Use CSS variables or theme context for theming
- Follow design system constraints
- Ensure accessibility (ARIA labels, keyboard navigation)
