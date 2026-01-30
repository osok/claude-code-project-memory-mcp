# Java Testing Conventions

## Test Structure

```
src/
├── main/
│   └── java/
│       └── com/company/project/
│           └── service/
│               └── UserService.java
└── test/
    └── java/
        └── com/company/project/
            ├── service/
            │   └── UserServiceTest.java      # Unit tests
            ├── integration/
            │   └── UserApiIntegrationTest.java
            └── fixtures/
                └── TestDataFactory.java
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test class | `{Class}Test` | `UserServiceTest` |
| Test method | `should{Action}_when{Condition}` | `shouldReturnUser_whenIdExists` |
| Integration test | `{Feature}IntegrationTest` | `UserApiIntegrationTest` |
| Fixture factory | `{Entity}TestFactory` | `UserTestFactory` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Test framework | JUnit 5 | Jupiter API |
| Assertions | AssertJ | Fluent assertions |
| Mocking | Mockito | With JUnit 5 extension |
| Spring testing | Spring Boot Test | @SpringBootTest |
| REST testing | MockMvc or WebTestClient | WebTestClient for reactive |
| Test containers | Testcontainers | For integration tests |
| Coverage | JaCoCo | Via build tool |

## Test Commands (Gradle)

| Action | Command |
|--------|---------|
| Run all | `./gradlew test` |
| Single class | `./gradlew test --tests UserServiceTest` |
| Single method | `./gradlew test --tests "UserServiceTest.shouldReturnUser*"` |
| Integration | `./gradlew integrationTest` |
| Coverage | `./gradlew jacocoTestReport` |
| Rerun failed | `./gradlew test --rerun-tasks` |

## Unit Test Structure

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EventPublisher eventPublisher;

    @InjectMocks
    private UserService userService;

    @Test
    void shouldReturnUser_whenIdExists() {
        // Given
        var userId = 1L;
        var expectedUser = new User(userId, "John");
        when(userRepository.findById(userId)).thenReturn(Optional.of(expectedUser));

        // When
        var result = userService.getUserById(userId);

        // Then
        assertThat(result)
            .isPresent()
            .hasValueSatisfying(user -> {
                assertThat(user.getId()).isEqualTo(userId);
                assertThat(user.getName()).isEqualTo("John");
            });
        verify(userRepository).findById(userId);
    }

    @Test
    void shouldThrowException_whenUserNotFound() {
        // Given
        var userId = 999L;
        when(userRepository.findById(userId)).thenReturn(Optional.empty());

        // When/Then
        assertThatThrownBy(() -> userService.getUserById(userId))
            .isInstanceOf(NotFoundException.class)
            .hasMessageContaining("User not found");
    }
}
```

## Parameterized Tests

```java
@ParameterizedTest
@CsvSource({
    "john@example.com, true",
    "jane@domain.co.uk, true",
    "invalid-email, false",
    "'', false"
})
void shouldValidateEmail(String email, boolean expectedValid) {
    boolean result = EmailValidator.isValid(email);

    assertThat(result).isEqualTo(expectedValid);
}

@ParameterizedTest
@MethodSource("provideUsersForValidation")
void shouldValidateUser(User user, boolean expectedValid) {
    boolean result = userValidator.isValid(user);

    assertThat(result).isEqualTo(expectedValid);
}

private static Stream<Arguments> provideUsersForValidation() {
    return Stream.of(
        Arguments.of(new User("John", "john@example.com"), true),
        Arguments.of(new User("", "john@example.com"), false),
        Arguments.of(new User("John", ""), false)
    );
}
```

## Spring Boot Integration Tests

```java
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureTestDatabase
class UserApiIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    void shouldCreateUser() {
        // Given
        var request = new CreateUserRequest("John", "john@example.com");

        // When
        var response = restTemplate.postForEntity("/api/users", request, UserDto.class);

        // Then
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody())
            .isNotNull()
            .satisfies(user -> {
                assertThat(user.getId()).isNotNull();
                assertThat(user.getName()).isEqualTo("John");
            });

        assertThat(userRepository.count()).isEqualTo(1);
    }
}
```

## MockMvc Testing

```java
@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UserService userService;

    @Test
    void shouldGetUser() throws Exception {
        // Given
        var user = new UserDto(1L, "John");
        when(userService.getUserById(1L)).thenReturn(Optional.of(user));

        // When/Then
        mockMvc.perform(get("/api/users/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(1))
            .andExpect(jsonPath("$.name").value("John"));
    }

    @Test
    void shouldReturn404_whenUserNotFound() throws Exception {
        when(userService.getUserById(999L)).thenReturn(Optional.empty());

        mockMvc.perform(get("/api/users/999"))
            .andExpect(status().isNotFound());
    }
}
```

## Test Data Factory

```java
public class UserTestFactory {

    public static User createUser() {
        return createUser(builder -> {});
    }

    public static User createUser(Consumer<User.UserBuilder> customizer) {
        var builder = User.builder()
            .id(1L)
            .name("Test User")
            .email("test@example.com")
            .createdAt(Instant.now());

        customizer.accept(builder);
        return builder.build();
    }

    public static List<User> createUsers(int count) {
        return IntStream.rangeClosed(1, count)
            .mapToObj(i -> createUser(b -> b.id((long) i).name("User " + i)))
            .toList();
    }
}
```

## Testcontainers

```java
@Testcontainers
@SpringBootTest
class UserRepositoryIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withDatabaseName("testdb");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private UserRepository userRepository;

    @Test
    void shouldSaveAndRetrieveUser() {
        var user = UserTestFactory.createUser();

        var saved = userRepository.save(user);
        var found = userRepository.findById(saved.getId());

        assertThat(found).isPresent();
    }
}
```

## Coverage Target

- Minimum: 70% line coverage
- Focus on service layer logic
- Exclude DTOs, configs, generated code
