# Java Conventions

## Project Structure

```
project/
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/company/project/
│   │   │       ├── Application.java      # Entry point
│   │   │       ├── config/               # Configuration classes
│   │   │       ├── controller/           # REST controllers
│   │   │       ├── service/              # Business logic
│   │   │       ├── repository/           # Data access
│   │   │       ├── model/                # Domain models
│   │   │       ├── dto/                  # Data transfer objects
│   │   │       └── exception/            # Custom exceptions
│   │   └── resources/
│   │       ├── application.yml
│   │       └── application-{env}.yml
│   └── test/
│       └── java/
│           └── com/company/project/
├── pom.xml (Maven) or build.gradle (Gradle)
└── README.md
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Package | lowercase, dot-separated | `com.company.project` |
| Class | PascalCase | `UserService` |
| Interface | PascalCase | `UserRepository` |
| Method | camelCase | `getUserById` |
| Variable | camelCase | `userCount` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_CONNECTIONS` |
| Enum values | SCREAMING_SNAKE_CASE | `USER_ACTIVE` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Framework | Spring Boot | Latest LTS version |
| Build tool | Gradle or Maven | Gradle preferred |
| ORM | Spring Data JPA | With Hibernate |
| Validation | Jakarta Validation | @Valid annotations |
| Mapping | MapStruct | Compile-time DTO mapping |
| Logging | SLF4J + Logback | Via Spring Boot |
| HTTP client | RestTemplate or WebClient | WebClient for reactive |
| JSON | Jackson | Spring Boot default |
| Testing | JUnit 5 + Mockito | Spring Boot Test |
| API docs | SpringDoc OpenAPI | Swagger UI |

## Build Commands (Gradle)

| Action | Command |
|--------|---------|
| Build | `./gradlew build` |
| Run | `./gradlew bootRun` |
| Test | `./gradlew test` |
| Clean | `./gradlew clean` |
| Package | `./gradlew bootJar` |
| Dependencies | `./gradlew dependencies` |

## Build Commands (Maven)

| Action | Command |
|--------|---------|
| Build | `./mvnw package` |
| Run | `./mvnw spring-boot:run` |
| Test | `./mvnw test` |
| Clean | `./mvnw clean` |
| Package | `./mvnw package -DskipTests` |

## Code Style

- Use constructor injection over field injection
- Prefer immutable objects
- Use Optional for nullable returns
- Keep methods under 30 lines
- One class per file
- Use records for DTOs (Java 17+)
- Avoid checked exceptions in business logic

## Class Structure

```java
@Service
@RequiredArgsConstructor // Lombok
public class UserService {

    private final UserRepository userRepository;
    private final UserMapper userMapper;

    public UserDto getUserById(Long id) {
        return userRepository.findById(id)
            .map(userMapper::toDto)
            .orElseThrow(() -> new NotFoundException("User not found: " + id));
    }
}
```

## Exception Handling

```java
// Custom exception
public class NotFoundException extends RuntimeException {
    public NotFoundException(String message) {
        super(message);
    }
}

// Global handler
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse(ex.getMessage()));
    }
}
```
