# Svelte Conventions

## Project Structure

```
project/
├── src/
│   ├── lib/
│   │   ├── components/       # Reusable components
│   │   │   └── ui/           # UI primitives
│   │   ├── stores/           # Svelte stores
│   │   ├── services/         # API services
│   │   ├── utils/            # Utility functions
│   │   └── types/            # TypeScript types
│   ├── routes/               # SvelteKit routes
│   │   ├── +layout.svelte
│   │   ├── +page.svelte
│   │   └── users/
│   │       ├── +page.svelte
│   │       └── [id]/
│   │           └── +page.svelte
│   ├── app.html
│   └── app.d.ts
├── static/
├── tests/
├── svelte.config.js
├── vite.config.ts
└── package.json
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Component | PascalCase | `UserProfile.svelte` |
| Route file | +page.svelte | `+page.svelte` |
| Layout | +layout.svelte | `+layout.svelte` |
| Server file | +page.server.ts | `+page.server.ts` |
| Store | camelCase | `userStore.ts` |
| Prop | camelCase | `userName` |
| Event | on:eventname | `on:click`, `on:submit` |
| CSS class | kebab-case | `user-profile` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Framework | SvelteKit | Full-stack framework |
| State | Svelte stores | Built-in |
| Forms | Superforms | Form handling |
| Validation | Zod | Schema validation |
| UI | Skeleton or shadcn-svelte | Component libraries |
| Icons | Lucide Svelte | Icon library |
| Testing | Vitest + Testing Library | Unit testing |
| E2E | Playwright | E2E testing |

## Build Commands

| Action | Command |
|--------|---------|
| Dev server | `npm run dev` |
| Build | `npm run build` |
| Preview | `npm run preview` |
| Test | `npm run test` |
| Lint | `npm run lint` |
| Format | `npm run format` |
| Check | `npm run check` |

## Component Structure (Svelte 5)

```svelte
<!-- UserProfile.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import type { User } from '$lib/types';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';

  // Props (Svelte 5 runes)
  let {
    userId,
    showDetails = false,
    ondelete
  }: {
    userId: string;
    showDetails?: boolean;
    ondelete?: () => void;
  } = $props();

  // State
  let user = $state<User | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  // Derived
  let userName = $derived(user?.name ?? 'Guest');

  // Effects
  $effect(() => {
    fetchUser(userId);
  });

  async function fetchUser(id: string) {
    loading = true;
    error = null;
    try {
      const response = await fetch(`/api/users/${id}`);
      user = await response.json();
    } catch (e) {
      error = 'Failed to load user';
    } finally {
      loading = false;
    }
  }

  function handleDelete() {
    ondelete?.();
  }
</script>

<div class="user-profile">
  {#if loading}
    <LoadingSpinner />
  {:else if error}
    <p class="error">{error}</p>
  {:else}
    <h1>{userName}</h1>
    {#if showDetails && user}
      <UserDetails {user} />
    {/if}
    <button onclick={handleDelete}>Delete</button>
  {/if}
</div>

<style>
  .user-profile {
    padding: 1rem;
  }

  .error {
    color: red;
  }
</style>
```

## Stores

```typescript
// stores/userStore.ts
import { writable, derived } from 'svelte/store';
import type { User } from '$lib/types';

function createUserStore() {
  const { subscribe, set, update } = writable<User | null>(null);

  return {
    subscribe,
    set,
    async fetch(id: string) {
      const response = await fetch(`/api/users/${id}`);
      const user = await response.json();
      set(user);
      return user;
    },
    clear() {
      set(null);
    }
  };
}

export const userStore = createUserStore();
export const isAuthenticated = derived(userStore, $user => !!$user);
```

## Server Load Functions

```typescript
// routes/users/[id]/+page.server.ts
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ params, fetch }) => {
  const response = await fetch(`/api/users/${params.id}`);

  if (!response.ok) {
    throw error(404, 'User not found');
  }

  const user = await response.json();

  return {
    user
  };
};
```

## Code Style

- Use Svelte 5 runes (`$state`, `$derived`, `$effect`, `$props`)
- Use TypeScript for type safety
- Keep components small and focused
- Use stores for shared state
- Colocate styles in components
- Use SvelteKit for routing and SSR
- Prefer server load functions for data fetching
- Use form actions for mutations
