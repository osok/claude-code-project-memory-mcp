# Kotlin Testing Conventions (Backend)

## Test Structure

```
src/
└── test/
    └── kotlin/
        └── com/example/
            ├── controller/
            │   └── UserControllerTest.kt
            ├── service/
            │   └── UserServiceTest.kt
            ├── repository/
            │   └── UserRepositoryTest.kt
            ├── integration/
            │   └── UserApiTest.kt
            └── fixtures/
                └── UserFixtures.kt
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test class | `{Class}Test` | `UserServiceTest` |
| Test function | Backticks with description | `` `should return user when exists` `` |
| Fixture | `{Entity}Fixtures` | `UserFixtures` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | Kotest | Kotlin-native, spec styles |
| Mocking | MockK | Kotlin-native mocking |
| Assertions | Kotest matchers | Fluent assertions |
| Spring testing | Spring Boot Test | Integration tests |
| HTTP testing | Ktor Test | For Ktor apps |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `./gradlew test` |
| Run specific | `./gradlew test --tests "UserServiceTest"` |
| Run pattern | `./gradlew test --tests "*User*"` |
| With coverage | `./gradlew test jacocoTestReport` |

## Unit Tests (Kotest)

```kotlin
class UserServiceTest : FunSpec({
    val userRepository = mockk<UserRepository>()
    val userService = UserService(userRepository)

    beforeTest {
        clearAllMocks()
    }

    test("should return user when exists") {
        // Arrange
        val userId = "123"
        val expectedUser = User(id = userId, name = "Test")
        coEvery { userRepository.findById(userId) } returns expectedUser

        // Act
        val result = userService.getUser(userId)

        // Assert
        result.shouldBeInstanceOf<Result.Success<User>>()
        result.value.name shouldBe "Test"
        coVerify(exactly = 1) { userRepository.findById(userId) }
    }

    test("should return failure when user not found") {
        // Arrange
        coEvery { userRepository.findById(any()) } returns null

        // Act
        val result = userService.getUser("non-existent")

        // Assert
        result.shouldBeInstanceOf<Result.Failure>()
        (result.error as AppError.NotFound).resource shouldBe "User"
    }

    context("when creating user") {
        test("should validate email format") {
            val request = CreateUserRequest(name = "Test", email = "invalid")

            val result = userService.createUser(request)

            result.shouldBeInstanceOf<Result.Failure>()
        }

        test("should save valid user") {
            val request = CreateUserRequest(name = "Test", email = "test@example.com")
            coEvery { userRepository.save(any()) } answers { firstArg() }

            val result = userService.createUser(request)

            result.shouldBeInstanceOf<Result.Success<User>>()
            coVerify { userRepository.save(any()) }
        }
    }
})
```

## Integration Tests (Spring)

```kotlin
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
class UserApiTest {
    @Autowired
    lateinit var mockMvc: MockMvc

    @Autowired
    lateinit var userRepository: UserRepository

    @BeforeEach
    fun setup() {
        userRepository.deleteAll()
    }

    @Test
    fun `GET users returns paginated list`() {
        // Arrange
        repeat(20) { userRepository.save(User(name = "User $it")) }

        // Act & Assert
        mockMvc.get("/api/users") {
            param("page", "0")
            param("size", "10")
        }.andExpect {
            status { isOk() }
            jsonPath("$.content.length()") { value(10) }
            jsonPath("$.totalElements") { value(20) }
        }
    }

    @Test
    fun `POST users creates user`() {
        val request = """{"name": "Test", "email": "test@example.com"}"""

        mockMvc.post("/api/users") {
            contentType = MediaType.APPLICATION_JSON
            content = request
        }.andExpect {
            status { isCreated() }
            jsonPath("$.name") { value("Test") }
        }

        userRepository.findAll() shouldHaveSize 1
    }
}
```

## MockK Usage

```kotlin
// Mock creation
val repository = mockk<UserRepository>()
val relaxedMock = mockk<Logger>(relaxed = true)  // Returns defaults

// Stubbing
every { repository.findById(any()) } returns User()
coEvery { repository.findByIdSuspend(any()) } returns User()  // For suspend functions

// Verification
verify { repository.findById("123") }
verify(exactly = 2) { repository.save(any()) }
coVerify { repository.findByIdSuspend(any()) }

// Argument capture
val slot = slot<User>()
every { repository.save(capture(slot)) } returns mockk()
// Later: slot.captured.name

// Answers
every { repository.save(any()) } answers { firstArg() }
```

## Test Fixtures

```kotlin
object UserFixtures {
    fun aUser(
        id: String = UUID.randomUUID().toString(),
        name: String = "Test User",
        email: String = "test@example.com",
        status: UserStatus = UserStatus.ACTIVE
    ) = User(
        id = id,
        name = name,
        email = email,
        status = status
    )

    fun aCreateUserRequest(
        name: String = "New User",
        email: String = "new@example.com"
    ) = CreateUserRequest(
        name = name,
        email = email
    )
}

// Usage
val user = UserFixtures.aUser(name = "Custom Name")
```

## Coverage Target

- Minimum: 80% line coverage
- Use JaCoCo for coverage reports
- Focus on business logic in services
