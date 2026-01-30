# Scala Conventions

## Project Structure

```
project/
├── src/
│   ├── main/
│   │   ├── scala/
│   │   │   └── com/example/
│   │   │       ├── Main.scala
│   │   │       ├── domain/
│   │   │       ├── service/
│   │   │       ├── repository/
│   │   │       └── http/
│   │   └── resources/
│   │       └── application.conf
│   └── test/
│       └── scala/
├── build.sbt
└── project/
    └── plugins.sbt
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Package | lowercase | `com.example.user` |
| Class/Object | PascalCase | `UserService` |
| Trait | PascalCase | `UserRepository` |
| Method | camelCase | `createUser` |
| Value | camelCase | `userName` |
| Constant | PascalCase | `MaxRetries` |
| Type parameter | Single uppercase | `F[_]`, `A`, `B` |
| Type alias | PascalCase | `type UserId = String` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Effect system | Cats Effect or ZIO | ZIO for batteries-included |
| HTTP | http4s or ZIO HTTP | Functional HTTP |
| JSON | Circe | Functional JSON |
| Database | Doobie or Quill | Functional DB access |
| Config | PureConfig | Typesafe config |
| Logging | log4cats | Functional logging |
| Testing | ScalaTest + ScalaCheck | Property-based |
| Streaming | fs2 | Functional streams |

## Build Commands

| Action | Command |
|--------|---------|
| Compile | `sbt compile` |
| Run | `sbt run` |
| Test | `sbt test` |
| Console | `sbt console` |
| Format | `sbt scalafmt` |
| Check format | `sbt scalafmtCheck` |
| Publish local | `sbt publishLocal` |

## Error Handling

```scala
// Use Either for errors
sealed trait AppError
case class NotFound(resource: String, id: String) extends AppError
case class ValidationError(message: String) extends AppError
case class DatabaseError(cause: Throwable) extends AppError

// Service with effect type
trait UserService[F[_]] {
  def getUser(id: String): F[Either[AppError, User]]
  def createUser(request: CreateUserRequest): F[Either[AppError, User]]
}

// Implementation with Cats Effect
class UserServiceImpl[F[_]: Async](
  repository: UserRepository[F]
) extends UserService[F] {

  def getUser(id: String): F[Either[AppError, User]] =
    repository.findById(id).map {
      case Some(user) => Right(user)
      case None       => Left(NotFound("User", id))
    }

  def createUser(request: CreateUserRequest): F[Either[AppError, User]] =
    for {
      validated <- validateRequest(request).pure[F]
      result <- validated.traverse(repository.save)
    } yield result
}
```

## Code Style

- Prefer immutability (`val` over `var`)
- Use case classes for data
- Use sealed traits for ADTs
- Prefer for-comprehensions for monadic operations
- Use type classes for polymorphism
- Avoid null; use Option
- Keep functions pure when possible
- Use meaningful type aliases
- Prefer composition over inheritance
