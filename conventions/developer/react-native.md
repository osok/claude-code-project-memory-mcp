# React Native Conventions

## Project Structure

```
src/
├── assets/                  # Images, fonts
├── components/
│   ├── ui/                  # Shared UI components
│   └── features/            # Feature-specific components
├── hooks/                   # Custom hooks
├── navigation/
│   ├── AppNavigator.tsx
│   └── types.ts
├── screens/
│   └── user/
│       ├── UserListScreen.tsx
│       └── UserDetailScreen.tsx
├── services/                # API services
├── stores/                  # State management
├── types/                   # TypeScript types
├── utils/                   # Utility functions
└── App.tsx
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Component | PascalCase | `UserCard.tsx` |
| Screen | PascalCase + Screen | `UserListScreen.tsx` |
| Hook | use + PascalCase | `useUser.ts` |
| Service | camelCase | `userService.ts` |
| Store | camelCase + Store | `userStore.ts` |
| Style | camelCase | `containerStyle` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Navigation | React Navigation | Standard |
| State | Zustand or Redux Toolkit | Zustand simpler |
| Forms | React Hook Form | Form handling |
| HTTP | Axios or TanStack Query | Query for caching |
| Storage | MMKV | Fast key-value |
| Testing | Jest + RNTL | React Native Testing Library |

## Build Commands

| Action | Command |
|--------|---------|
| Start Metro | `npm start` |
| Run iOS | `npm run ios` |
| Run Android | `npm run android` |
| Test | `npm test` |
| Lint | `npm run lint` |
| TypeScript | `npm run typecheck` |

## Screen Component

```tsx
// screens/user/UserListScreen.tsx
import { FlatList, StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useUsers } from '@/hooks/useUsers';
import { UserCard } from '@/components/features/UserCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorMessage } from '@/components/ui/ErrorMessage';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '@/navigation/types';

type NavigationProp = NativeStackNavigationProp<RootStackParamList, 'UserList'>;

export function UserListScreen() {
  const navigation = useNavigation<NavigationProp>();
  const { users, isLoading, error, refetch } = useUsers();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage message={error.message} onRetry={refetch} />;
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={users}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <UserCard
            user={item}
            onPress={() => navigation.navigate('UserDetail', { userId: item.id })}
          />
        )}
        onRefresh={refetch}
        refreshing={isLoading}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
});
```

## Custom Hook with TanStack Query

```tsx
// hooks/useUsers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '@/services/userService';
import type { User, CreateUserInput } from '@/types';

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: userService.getUsers,
  });
}

export function useUser(id: string) {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => userService.getUser(id),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateUserInput) => userService.createUser(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
```

## Zustand Store

```tsx
// stores/authStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV();

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setUser: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setUser: (user, token) =>
        set({ user, token, isAuthenticated: true }),
      logout: () =>
        set({ user: null, token: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => ({
        setItem: (name, value) => storage.set(name, value),
        getItem: (name) => storage.getString(name) ?? null,
        removeItem: (name) => storage.delete(name),
      })),
    }
  )
);
```

## Navigation Setup

```tsx
// navigation/AppNavigator.tsx
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { UserListScreen } from '@/screens/user/UserListScreen';
import { UserDetailScreen } from '@/screens/user/UserDetailScreen';
import type { RootStackParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="UserList">
        <Stack.Screen
          name="UserList"
          component={UserListScreen}
          options={{ title: 'Users' }}
        />
        <Stack.Screen
          name="UserDetail"
          component={UserDetailScreen}
          options={{ title: 'User Details' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

// navigation/types.ts
export type RootStackParamList = {
  UserList: undefined;
  UserDetail: { userId: string };
};
```

## Code Style

- Use functional components with hooks
- Keep components small and focused
- Colocate styles with components
- Use TypeScript for type safety
- Extract business logic to hooks
- Use React Navigation for routing
- Prefer MMKV over AsyncStorage
- Test with React Native Testing Library
