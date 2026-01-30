# Nuxt Conventions

## Project Structure

```
project/
├── assets/                 # Uncompiled assets (SCSS, images)
├── components/
│   ├── ui/                 # Shared UI components
│   └── features/           # Feature-specific components
├── composables/            # Auto-imported composables
├── layouts/                # Layout components
├── middleware/             # Route middleware
├── pages/                  # File-based routing
│   ├── index.vue
│   └── users/
│       ├── index.vue
│       └── [id].vue
├── plugins/                # Nuxt plugins
├── public/                 # Static files
├── server/
│   ├── api/                # API routes
│   │   └── users/
│   │       ├── index.ts
│   │       └── [id].ts
│   ├── middleware/         # Server middleware
│   └── utils/              # Server utilities
├── stores/                 # Pinia stores
├── types/                  # TypeScript types
├── utils/                  # Auto-imported utilities
├── app.vue
├── nuxt.config.ts
└── package.json
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Component | PascalCase | `UserProfile.vue` |
| Page | kebab-case | `user-profile.vue` |
| Composable | use + camelCase | `useAuth.ts` |
| Store | camelCase | `userStore.ts` |
| API route | kebab-case | `user-profile.ts` |
| Middleware | kebab-case | `auth.ts` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| State | Pinia | Built-in support |
| Validation | Zod | Schema validation |
| Forms | VeeValidate | Form handling |
| UI | Nuxt UI or PrimeVue | Component libraries |
| Icons | Nuxt Icon | Icon support |
| Images | Nuxt Image | Image optimization |
| Testing | Vitest + Nuxt Test Utils | Testing support |

## Build Commands

| Action | Command |
|--------|---------|
| Dev server | `npm run dev` |
| Build | `npm run build` |
| Preview | `npm run preview` |
| Generate | `npm run generate` |
| Test | `npm run test` |
| Lint | `npm run lint` |

## Page Components

```vue
<!-- pages/users/[id].vue -->
<script setup lang="ts">
definePageMeta({
  middleware: ['auth'],
});

const route = useRoute();
const { id } = route.params;

// Server-side data fetching
const { data: user, pending, error } = await useFetch(`/api/users/${id}`);

// SEO
useSeoMeta({
  title: () => user.value?.name ?? 'User',
  description: () => `Profile for ${user.value?.name}`,
});
</script>

<template>
  <div class="user-page">
    <LoadingSpinner v-if="pending" />
    <ErrorMessage v-else-if="error" :message="error.message" />
    <template v-else-if="user">
      <h1>{{ user.name }}</h1>
      <UserDetails :user="user" />
    </template>
  </div>
</template>
```

## Composables

```typescript
// composables/useAuth.ts
export function useAuth() {
  const user = useState<User | null>('user', () => null);
  const isAuthenticated = computed(() => !!user.value);

  async function login(email: string, password: string) {
    const { data } = await useFetch('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    user.value = data.value;
    navigateTo('/dashboard');
  }

  async function logout() {
    await useFetch('/api/auth/logout', { method: 'POST' });
    user.value = null;
    navigateTo('/login');
  }

  return {
    user: readonly(user),
    isAuthenticated,
    login,
    logout,
  };
}
```

## Server API Routes

```typescript
// server/api/users/index.ts
export default defineEventHandler(async (event) => {
  const query = getQuery(event);
  const page = parseInt(query.page as string) || 1;

  const users = await prisma.user.findMany({
    skip: (page - 1) * 10,
    take: 10,
  });

  return users;
});

// server/api/users/index.post.ts
export default defineEventHandler(async (event) => {
  const body = await readBody(event);

  // Validate
  const schema = z.object({
    name: z.string().min(1),
    email: z.string().email(),
  });

  const validated = schema.safeParse(body);
  if (!validated.success) {
    throw createError({
      statusCode: 400,
      message: 'Invalid data',
    });
  }

  const user = await prisma.user.create({
    data: validated.data,
  });

  setResponseStatus(event, 201);
  return user;
});

// server/api/users/[id].ts
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id');

  const user = await prisma.user.findUnique({
    where: { id },
  });

  if (!user) {
    throw createError({
      statusCode: 404,
      message: 'User not found',
    });
  }

  return user;
});
```

## Middleware

```typescript
// middleware/auth.ts
export default defineNuxtRouteMiddleware((to, from) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated.value) {
    return navigateTo('/login');
  }
});

// middleware/auth.global.ts (runs on every route)
export default defineNuxtRouteMiddleware((to) => {
  const publicPaths = ['/login', '/register', '/'];

  if (publicPaths.includes(to.path)) {
    return;
  }

  const { isAuthenticated } = useAuth();
  if (!isAuthenticated.value) {
    return navigateTo('/login');
  }
});
```

## Code Style

- Use Composition API with `<script setup>`
- Use auto-imports (no manual imports for Vue/Nuxt APIs)
- Use `useFetch` for data fetching (SSR-friendly)
- Use `useState` for SSR-safe reactive state
- Keep API routes simple, use utilities for logic
- Use Pinia for complex global state
- Use middleware for route guards
