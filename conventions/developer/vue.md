# Vue Conventions

## Project Structure

```
project/
├── src/
│   ├── assets/              # Static assets
│   ├── components/
│   │   ├── common/          # Shared components
│   │   └── feature/         # Feature-specific components
│   ├── composables/         # Composition API hooks
│   ├── layouts/             # Layout components
│   ├── pages/               # Route pages (if using file-based routing)
│   ├── router/
│   │   └── index.ts
│   ├── stores/              # Pinia stores
│   ├── services/            # API services
│   ├── types/               # TypeScript types
│   ├── utils/               # Utility functions
│   ├── App.vue
│   └── main.ts
├── public/
├── tests/
├── package.json
└── vite.config.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Component file | PascalCase | `UserProfile.vue` |
| Component name | PascalCase | `UserProfile` |
| Composable | use + camelCase | `useAuth`, `useFetch` |
| Store | camelCase + Store | `userStore`, `authStore` |
| Props | camelCase | `userName`, `isActive` |
| Events | kebab-case | `@update-user`, `@form-submit` |
| Route | kebab-case | `/user-profile` |
| CSS class | kebab-case or BEM | `user-card`, `user-card__title` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| State management | Pinia | Official, replaces Vuex |
| Routing | Vue Router | Official router |
| HTTP client | Axios or fetch | Axios with interceptors |
| Forms | VeeValidate | Form validation |
| UI components | Vuetify, PrimeVue, or Headless UI | Pick one |
| Icons | unplugin-icons | Any icon set |
| Testing | Vitest + Vue Test Utils | Official testing |
| E2E | Playwright or Cypress | Playwright preferred |

## Build Commands

| Action | Command |
|--------|---------|
| Dev server | `npm run dev` |
| Build | `npm run build` |
| Preview | `npm run preview` |
| Test | `npm run test` |
| Test UI | `npm run test:ui` |
| Lint | `npm run lint` |
| Type check | `npm run type-check` |

## Component Structure

```vue
<script setup lang="ts">
// Imports
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import type { User } from '@/types'

// Props
const props = defineProps<{
  userId: string
  showDetails?: boolean
}>()

// Emits
const emit = defineEmits<{
  'update-user': [user: User]
  'delete': []
}>()

// Composables
const userStore = useUserStore()

// Reactive state
const isLoading = ref(false)
const error = ref<string | null>(null)

// Computed
const userName = computed(() => userStore.currentUser?.name ?? 'Guest')

// Methods
async function fetchUser() {
  isLoading.value = true
  try {
    await userStore.fetchUser(props.userId)
  } catch (e) {
    error.value = 'Failed to load user'
  } finally {
    isLoading.value = false
  }
}

// Lifecycle
onMounted(() => {
  fetchUser()
})
</script>

<template>
  <div class="user-profile">
    <LoadingSpinner v-if="isLoading" />
    <ErrorMessage v-else-if="error" :message="error" />
    <template v-else>
      <h1>{{ userName }}</h1>
      <UserDetails v-if="showDetails" :user="userStore.currentUser" />
      <button @click="emit('delete')">Delete</button>
    </template>
  </div>
</template>

<style scoped>
.user-profile {
  padding: 1rem;
}
</style>
```

## Composables

```typescript
// composables/useAuth.ts
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '@/services/auth'

export function useAuth() {
  const router = useRouter()
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => !!user.value)

  async function login(email: string, password: string) {
    user.value = await authService.login(email, password)
    router.push('/dashboard')
  }

  async function logout() {
    await authService.logout()
    user.value = null
    router.push('/login')
  }

  return {
    user,
    isAuthenticated,
    login,
    logout,
  }
}
```

## Code Style

- Use Composition API with `<script setup>`
- Use TypeScript for type safety
- Keep components small and focused
- Extract logic to composables
- Use Pinia for global state
- Prefer scoped styles
- Use `v-bind` shorthand (`:prop`)
- Use `v-on` shorthand (`@event`)
