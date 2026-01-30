# Kotlin Android Conventions

## Project Structure

```
app/
├── src/
│   ├── main/
│   │   ├── java/com/example/app/
│   │   │   ├── data/
│   │   │   │   ├── local/           # Room database
│   │   │   │   ├── remote/          # API services
│   │   │   │   └── repository/
│   │   │   ├── di/                  # Dependency injection
│   │   │   ├── domain/
│   │   │   │   ├── model/           # Domain models
│   │   │   │   └── usecase/         # Use cases
│   │   │   ├── ui/
│   │   │   │   ├── theme/           # Compose theme
│   │   │   │   ├── components/      # Reusable composables
│   │   │   │   └── screens/         # Screen composables
│   │   │   │       └── user/
│   │   │   │           ├── UserScreen.kt
│   │   │   │           └── UserViewModel.kt
│   │   │   └── App.kt               # Application class
│   │   ├── res/
│   │   └── AndroidManifest.xml
│   ├── test/                        # Unit tests
│   └── androidTest/                 # Instrumented tests
├── build.gradle.kts
└── proguard-rules.pro
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Package | lowercase | `com.example.user` |
| Class | PascalCase | `UserViewModel` |
| Composable | PascalCase | `UserScreen` |
| Function | camelCase | `loadUser` |
| Property | camelCase | `userName` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_RETRY` |
| Resource ID | snake_case | `@id/user_name` |
| Layout file | snake_case | `activity_main.xml` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| UI | Jetpack Compose | Modern UI toolkit |
| DI | Hilt | Official DI |
| Networking | Retrofit + OkHttp | HTTP client |
| JSON | Moshi or kotlinx.serialization | JSON parsing |
| Database | Room | SQLite abstraction |
| Navigation | Navigation Compose | Jetpack Navigation |
| State | ViewModel + StateFlow | State management |
| Image loading | Coil | Compose-first |
| Testing | JUnit + Mockk | Unit testing |

## Build Commands

| Action | Command |
|--------|---------|
| Build | `./gradlew assembleDebug` |
| Build release | `./gradlew assembleRelease` |
| Test | `./gradlew test` |
| Android tests | `./gradlew connectedAndroidTest` |
| Lint | `./gradlew lint` |
| Clean | `./gradlew clean` |

## Compose Screen Pattern

```kotlin
// ui/screens/user/UserScreen.kt
@Composable
fun UserScreen(
    viewModel: UserViewModel = hiltViewModel(),
    onNavigateToDetails: (String) -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    UserScreenContent(
        uiState = uiState,
        onRefresh = viewModel::refresh,
        onUserClick = onNavigateToDetails
    )
}

@Composable
private fun UserScreenContent(
    uiState: UserUiState,
    onRefresh: () -> Unit,
    onUserClick: (String) -> Unit
) {
    when (uiState) {
        is UserUiState.Loading -> LoadingIndicator()
        is UserUiState.Error -> ErrorMessage(
            message = uiState.message,
            onRetry = onRefresh
        )
        is UserUiState.Success -> UserList(
            users = uiState.users,
            onUserClick = onUserClick
        )
    }
}

@Composable
private fun UserList(
    users: List<User>,
    onUserClick: (String) -> Unit
) {
    LazyColumn {
        items(users, key = { it.id }) { user ->
            UserItem(
                user = user,
                onClick = { onUserClick(user.id) }
            )
        }
    }
}
```

## ViewModel Pattern

```kotlin
// ui/screens/user/UserViewModel.kt
@HiltViewModel
class UserViewModel @Inject constructor(
    private val getUsersUseCase: GetUsersUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<UserUiState>(UserUiState.Loading)
    val uiState: StateFlow<UserUiState> = _uiState.asStateFlow()

    init {
        loadUsers()
    }

    fun refresh() {
        loadUsers()
    }

    private fun loadUsers() {
        viewModelScope.launch {
            _uiState.value = UserUiState.Loading
            getUsersUseCase()
                .onSuccess { users ->
                    _uiState.value = UserUiState.Success(users)
                }
                .onFailure { error ->
                    _uiState.value = UserUiState.Error(error.message ?: "Unknown error")
                }
        }
    }
}

sealed interface UserUiState {
    data object Loading : UserUiState
    data class Success(val users: List<User>) : UserUiState
    data class Error(val message: String) : UserUiState
}
```

## Repository Pattern

```kotlin
// data/repository/UserRepository.kt
interface UserRepository {
    suspend fun getUsers(): Result<List<User>>
    suspend fun getUser(id: String): Result<User>
    suspend fun createUser(request: CreateUserRequest): Result<User>
}

class UserRepositoryImpl @Inject constructor(
    private val api: UserApi,
    private val userDao: UserDao
) : UserRepository {

    override suspend fun getUsers(): Result<List<User>> = runCatching {
        val users = api.getUsers()
        userDao.insertAll(users.map { it.toEntity() })
        users
    }.recoverCatching {
        // Fallback to cache
        userDao.getAll().map { it.toUser() }
    }

    override suspend fun getUser(id: String): Result<User> = runCatching {
        api.getUser(id)
    }
}
```

## Code Style

- Use Jetpack Compose for all new UI
- Follow MVVM + Clean Architecture
- Use Hilt for dependency injection
- Use StateFlow for reactive state
- Keep composables small and focused
- Extract stateless composables for testing
- Use sealed interfaces for UI state
- Handle errors gracefully with Result type
