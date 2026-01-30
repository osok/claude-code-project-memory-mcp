# React Native Testing Conventions

## Test Structure

```
__tests__/
├── components/
│   └── UserCard.test.tsx
├── screens/
│   └── UserListScreen.test.tsx
├── hooks/
│   └── useUsers.test.tsx
└── utils/
    └── formatters.test.ts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{Component}.test.tsx` | `UserCard.test.tsx` |
| Test suite | `describe('{Component}')` | `describe('UserCard')` |
| Test case | Describes behavior | `it('displays user name')` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | Jest | Standard |
| Component testing | React Native Testing Library | @testing-library/react-native |
| Mocking | Jest | Built-in |
| E2E | Detox | Optional |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `npm test` |
| Watch | `npm test -- --watch` |
| Coverage | `npm test -- --coverage` |
| Specific | `npm test -- UserCard` |

## Component Tests

```tsx
import { render, screen, fireEvent } from '@testing-library/react-native';
import { UserCard } from '@/components/features/UserCard';

describe('UserCard', () => {
  const mockUser = {
    id: '1',
    name: 'Test User',
    email: 'test@example.com',
  };

  it('displays user name', () => {
    render(<UserCard user={mockUser} onPress={jest.fn()} />);

    expect(screen.getByText('Test User')).toBeTruthy();
  });

  it('displays user email', () => {
    render(<UserCard user={mockUser} onPress={jest.fn()} />);

    expect(screen.getByText('test@example.com')).toBeTruthy();
  });

  it('calls onPress when pressed', () => {
    const onPress = jest.fn();
    render(<UserCard user={mockUser} onPress={onPress} />);

    fireEvent.press(screen.getByTestId('user-card'));

    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
```

## Screen Tests

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UserListScreen } from '@/screens/user/UserListScreen';
import { userService } from '@/services/userService';

jest.mock('@/services/userService');

const mockNavigation = {
  navigate: jest.fn(),
};

jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => mockNavigation,
}));

function renderWithProviders(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <NavigationContainer>
        {component}
      </NavigationContainer>
    </QueryClientProvider>
  );
}

describe('UserListScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading indicator initially', () => {
    (userService.getUsers as jest.Mock).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<UserListScreen />);

    expect(screen.getByTestId('loading-spinner')).toBeTruthy();
  });

  it('displays users after loading', async () => {
    const users = [
      { id: '1', name: 'User One', email: 'one@example.com' },
      { id: '2', name: 'User Two', email: 'two@example.com' },
    ];
    (userService.getUsers as jest.Mock).mockResolvedValue(users);

    renderWithProviders(<UserListScreen />);

    await waitFor(() => {
      expect(screen.getByText('User One')).toBeTruthy();
      expect(screen.getByText('User Two')).toBeTruthy();
    });
  });

  it('shows error message on failure', async () => {
    (userService.getUsers as jest.Mock).mockRejectedValue(new Error('Network error'));

    renderWithProviders(<UserListScreen />);

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeTruthy();
    });
  });

  it('navigates to detail screen on user press', async () => {
    const users = [{ id: '1', name: 'User One', email: 'one@example.com' }];
    (userService.getUsers as jest.Mock).mockResolvedValue(users);

    renderWithProviders(<UserListScreen />);

    await waitFor(() => {
      expect(screen.getByText('User One')).toBeTruthy();
    });

    fireEvent.press(screen.getByText('User One'));

    expect(mockNavigation.navigate).toHaveBeenCalledWith('UserDetail', { userId: '1' });
  });
});
```

## Hook Tests

```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUsers, useCreateUser } from '@/hooks/useUsers';
import { userService } from '@/services/userService';

jest.mock('@/services/userService');

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('useUsers', () => {
  it('returns users on success', async () => {
    const users = [{ id: '1', name: 'Test' }];
    (userService.getUsers as jest.Mock).mockResolvedValue(users);

    const { result } = renderHook(() => useUsers(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(users);
  });

  it('returns error on failure', async () => {
    (userService.getUsers as jest.Mock).mockRejectedValue(new Error('Failed'));

    const { result } = renderHook(() => useUsers(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe('Failed');
  });
});

describe('useCreateUser', () => {
  it('creates user and invalidates cache', async () => {
    const newUser = { id: '2', name: 'New User' };
    (userService.createUser as jest.Mock).mockResolvedValue(newUser);

    const { result } = renderHook(() => useCreateUser(), { wrapper });

    result.current.mutate({ name: 'New User', email: 'new@example.com' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});
```

## Store Tests

```tsx
import { renderHook, act } from '@testing-library/react-native';
import { useAuthStore } from '@/stores/authStore';

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  });

  it('sets user on login', () => {
    const { result } = renderHook(() => useAuthStore());
    const user = { id: '1', name: 'Test' };

    act(() => {
      result.current.setUser(user, 'token123');
    });

    expect(result.current.user).toEqual(user);
    expect(result.current.token).toBe('token123');
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('clears state on logout', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setUser({ id: '1', name: 'Test' }, 'token');
      result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });
});
```

## Test Utilities

```tsx
// __tests__/utils/test-utils.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NavigationContainer } from '@react-navigation/native';

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

export function AllProviders({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <NavigationContainer>
        {children}
      </NavigationContainer>
    </QueryClientProvider>
  );
}
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on screens, hooks, and stores
- Test user interactions, not implementation
