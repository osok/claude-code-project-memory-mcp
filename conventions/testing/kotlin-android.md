# Kotlin Android Testing Conventions

## Test Structure

```
app/src/
├── test/                           # Unit tests (JVM)
│   └── java/com/example/app/
│       ├── data/
│       │   └── repository/
│       │       └── UserRepositoryTest.kt
│       ├── domain/
│       │   └── usecase/
│       │       └── GetUsersUseCaseTest.kt
│       └── ui/
│           └── screens/
│               └── user/
│                   └── UserViewModelTest.kt
└── androidTest/                    # Instrumented tests
    └── java/com/example/app/
        ├── ui/
        │   └── screens/
        │       └── UserScreenTest.kt
        └── data/
            └── local/
                └── UserDaoTest.kt
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test class | `{Class}Test` | `UserViewModelTest` |
| Test method | Backticks with description | `` `should load users on init` `` |
| Fake | `Fake{Interface}` | `FakeUserRepository` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Unit tests | JUnit 5 | Standard |
| Mocking | MockK | Kotlin-native |
| Coroutines | Turbine | Flow testing |
| Compose | Compose Testing | UI tests |
| Android | Robolectric | JVM Android |

## Test Commands

| Action | Command |
|--------|---------|
| Unit tests | `./gradlew test` |
| Android tests | `./gradlew connectedAndroidTest` |
| Specific test | `./gradlew test --tests "*UserViewModel*"` |
| Coverage | `./gradlew jacocoTestReport` |

## ViewModel Tests

```kotlin
@OptIn(ExperimentalCoroutinesApi::class)
class UserViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private lateinit var getUsersUseCase: GetUsersUseCase
    private lateinit var viewModel: UserViewModel

    @BeforeEach
    fun setup() {
        getUsersUseCase = mockk()
    }

    @Test
    fun `should show loading then success when users load`() = runTest {
        // Arrange
        val users = listOf(User("1", "Test"))
        coEvery { getUsersUseCase() } returns Result.success(users)

        // Act
        viewModel = UserViewModel(getUsersUseCase)

        // Assert
        viewModel.uiState.test {
            assertThat(awaitItem()).isEqualTo(UserUiState.Loading)
            assertThat(awaitItem()).isEqualTo(UserUiState.Success(users))
        }
    }

    @Test
    fun `should show error when loading fails`() = runTest {
        // Arrange
        coEvery { getUsersUseCase() } returns Result.failure(Exception("Network error"))

        // Act
        viewModel = UserViewModel(getUsersUseCase)

        // Assert
        viewModel.uiState.test {
            assertThat(awaitItem()).isEqualTo(UserUiState.Loading)
            val error = awaitItem() as UserUiState.Error
            assertThat(error.message).isEqualTo("Network error")
        }
    }

    @Test
    fun `refresh should reload users`() = runTest {
        // Arrange
        val users = listOf(User("1", "Test"))
        coEvery { getUsersUseCase() } returns Result.success(users)
        viewModel = UserViewModel(getUsersUseCase)

        // Act
        viewModel.refresh()

        // Assert
        coVerify(exactly = 2) { getUsersUseCase() }
    }
}

// Test rule for main dispatcher
class MainDispatcherRule(
    private val dispatcher: TestDispatcher = UnconfinedTestDispatcher()
) : TestWatcher() {
    override fun starting(description: Description) {
        Dispatchers.setMain(dispatcher)
    }

    override fun finished(description: Description) {
        Dispatchers.resetMain()
    }
}
```

## Repository Tests

```kotlin
class UserRepositoryTest {

    private lateinit var api: UserApi
    private lateinit var dao: UserDao
    private lateinit var repository: UserRepository

    @BeforeEach
    fun setup() {
        api = mockk()
        dao = mockk(relaxed = true)
        repository = UserRepositoryImpl(api, dao)
    }

    @Test
    fun `getUsers should return from API and cache`() = runTest {
        // Arrange
        val users = listOf(User("1", "Test"))
        coEvery { api.getUsers() } returns users

        // Act
        val result = repository.getUsers()

        // Assert
        assertThat(result.isSuccess).isTrue()
        assertThat(result.getOrNull()).isEqualTo(users)
        coVerify { dao.insertAll(any()) }
    }

    @Test
    fun `getUsers should fallback to cache on API error`() = runTest {
        // Arrange
        val cachedEntities = listOf(UserEntity("1", "Cached"))
        coEvery { api.getUsers() } throws IOException()
        coEvery { dao.getAll() } returns cachedEntities

        // Act
        val result = repository.getUsers()

        // Assert
        assertThat(result.isSuccess).isTrue()
        assertThat(result.getOrNull()?.first()?.name).isEqualTo("Cached")
    }
}
```

## Compose UI Tests

```kotlin
@OptIn(ExperimentalTestApi::class)
class UserScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun `displays loading indicator when loading`() {
        composeTestRule.setContent {
            UserScreenContent(
                uiState = UserUiState.Loading,
                onRefresh = {},
                onUserClick = {}
            )
        }

        composeTestRule.onNodeWithTag("loading").assertIsDisplayed()
    }

    @Test
    fun `displays users when loaded`() {
        val users = listOf(
            User("1", "User One"),
            User("2", "User Two")
        )

        composeTestRule.setContent {
            UserScreenContent(
                uiState = UserUiState.Success(users),
                onRefresh = {},
                onUserClick = {}
            )
        }

        composeTestRule.onNodeWithText("User One").assertIsDisplayed()
        composeTestRule.onNodeWithText("User Two").assertIsDisplayed()
    }

    @Test
    fun `calls onUserClick when user tapped`() {
        var clickedId: String? = null
        val users = listOf(User("1", "User One"))

        composeTestRule.setContent {
            UserScreenContent(
                uiState = UserUiState.Success(users),
                onRefresh = {},
                onUserClick = { clickedId = it }
            )
        }

        composeTestRule.onNodeWithText("User One").performClick()

        assertThat(clickedId).isEqualTo("1")
    }

    @Test
    fun `displays error message and retry button`() {
        var refreshCalled = false

        composeTestRule.setContent {
            UserScreenContent(
                uiState = UserUiState.Error("Something went wrong"),
                onRefresh = { refreshCalled = true },
                onUserClick = {}
            )
        }

        composeTestRule.onNodeWithText("Something went wrong").assertIsDisplayed()
        composeTestRule.onNodeWithText("Retry").performClick()

        assertThat(refreshCalled).isTrue()
    }
}
```

## Room DAO Tests

```kotlin
@RunWith(AndroidJUnit4::class)
class UserDaoTest {

    private lateinit var database: AppDatabase
    private lateinit var dao: UserDao

    @Before
    fun setup() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            AppDatabase::class.java
        ).build()
        dao = database.userDao()
    }

    @After
    fun teardown() {
        database.close()
    }

    @Test
    fun insertAndRetrieveUser() = runTest {
        val user = UserEntity("1", "Test User")

        dao.insert(user)
        val retrieved = dao.getById("1")

        assertThat(retrieved).isEqualTo(user)
    }

    @Test
    fun getAllReturnsAllUsers() = runTest {
        val users = listOf(
            UserEntity("1", "User One"),
            UserEntity("2", "User Two")
        )

        dao.insertAll(users)
        val retrieved = dao.getAll()

        assertThat(retrieved).hasSize(2)
    }
}
```

## Test Fakes

```kotlin
class FakeUserRepository : UserRepository {
    private val users = mutableListOf<User>()
    var shouldFail = false
    var failureMessage = "Error"

    override suspend fun getUsers(): Result<List<User>> {
        return if (shouldFail) {
            Result.failure(Exception(failureMessage))
        } else {
            Result.success(users.toList())
        }
    }

    fun addUser(user: User) {
        users.add(user)
    }

    fun clear() {
        users.clear()
        shouldFail = false
    }
}
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on ViewModels, repositories, and use cases
- Test Compose UI with stateless content composables
