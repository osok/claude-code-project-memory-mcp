# Kotlin Conventions (Backend)

## Project Structure

```
project/
├── src/
│   ├── main/
│   │   ├── kotlin/
│   │   │   └── com/example/
│   │   │       ├── Application.kt
│   │   │       ├── config/
│   │   │       ├── controller/
│   │   │       ├── service/
│   │   │       ├── repository/
│   │   │       ├── model/
│   │   │       └── dto/
│   │   └── resources/
│   │       └── application.yml
│   └── test/
│       └── kotlin/
├── build.gradle.kts
└── settings.gradle.kts
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Package | lowercase, dot-separated | `com.example.user` |
| Class | PascalCase | `UserService` |
| Interface | PascalCase | `UserRepository` |
| Function | camelCase | `createUser` |
| Property | camelCase | `userName` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| Enum | PascalCase | `UserStatus.ACTIVE` |
| File | PascalCase | `UserService.kt` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Framework | Spring Boot or Ktor | Spring Boot for enterprise |
| ORM | Exposed or Spring Data JPA | Exposed for Kotlin-first |
| HTTP client | Ktor Client | Kotlin-native |
| Serialization | kotlinx.serialization | Kotlin-native |
| Coroutines | kotlinx.coroutines | Async programming |
| DI | Koin or Spring DI | Koin for Kotlin-first |
| Validation | konform | Kotlin DSL validation |
| Testing | Kotest | Kotlin-native testing |

## Build Commands

| Action | Command |
|--------|---------|
| Build | `./gradlew build` |
| Run | `./gradlew bootRun` or `./gradlew run` |
| Test | `./gradlew test` |
| Clean | `./gradlew clean` |
| Format | `./gradlew ktlintFormat` |
| Lint | `./gradlew ktlintCheck` |

## Error Handling

```kotlin
// Sealed class for results
sealed class Result<out T> {
    data class Success<T>(val value: T) : Result<T>()
    data class Failure(val error: AppError) : Result<Nothing>()
}

sealed class AppError {
    data class NotFound(val resource: String, val id: String) : AppError()
    data class Validation(val message: String) : AppError()
    data class Unauthorized(val message: String) : AppError()
}

// Extension functions for Result
inline fun <T, R> Result<T>.map(transform: (T) -> R): Result<R> = when (this) {
    is Result.Success -> Result.Success(transform(value))
    is Result.Failure -> this
}

// Service usage
class UserService(private val repository: UserRepository) {
    suspend fun getUser(id: String): Result<User> {
        return repository.findById(id)
            ?.let { Result.Success(it) }
            ?: Result.Failure(AppError.NotFound("User", id))
    }
}
```

## Code Style

- Use data classes for DTOs and value objects
- Prefer immutability (`val` over `var`)
- Use null safety features (`?.`, `?:`, `!!` sparingly)
- Use extension functions for utility methods
- Use scope functions appropriately (`let`, `run`, `with`, `apply`, `also`)
- Use coroutines for async operations
- Prefer expression bodies for simple functions
- Use sealed classes for restricted hierarchies
