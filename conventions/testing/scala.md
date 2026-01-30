# Scala Testing Conventions

## Test Structure

```
src/
└── test/
    └── scala/
        └── com/example/
            ├── service/
            │   └── UserServiceSpec.scala
            ├── repository/
            │   └── UserRepositorySpec.scala
            ├── http/
            │   └── UserRoutesSpec.scala
            ├── integration/
            │   └── UserApiSpec.scala
            └── fixtures/
                └── UserFixtures.scala
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test class | `{Class}Spec` | `UserServiceSpec` |
| Test | Descriptive string | `"return user when exists"` |
| Property test | `forAll` description | `"handle any valid email"` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | ScalaTest or MUnit | MUnit simpler |
| Mocking | ScalaMock or Mockito | ScalaMock for Scala |
| Property testing | ScalaCheck | Generative testing |
| Effect testing | Cats Effect Test | For IO testing |
| HTTP testing | http4s-dsl | Route testing |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `sbt test` |
| Run specific | `sbt "testOnly *UserServiceSpec"` |
| Run pattern | `sbt "testOnly *User*"` |
| Continuous | `sbt ~test` |
| Coverage | `sbt coverage test coverageReport` |

## Unit Tests (ScalaTest)

```scala
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import org.scalamock.scalatest.MockFactory
import cats.effect.IO
import cats.effect.unsafe.implicits.global

class UserServiceSpec extends AnyFlatSpec with Matchers with MockFactory {

  val mockRepository = mock[UserRepository[IO]]
  val service = new UserServiceImpl[IO](mockRepository)

  "UserService.getUser" should "return user when exists" in {
    val userId = "123"
    val expectedUser = User(id = userId, name = "Test")

    (mockRepository.findById _)
      .expects(userId)
      .returning(IO.pure(Some(expectedUser)))

    val result = service.getUser(userId).unsafeRunSync()

    result shouldBe Right(expectedUser)
  }

  it should "return NotFound when user doesn't exist" in {
    (mockRepository.findById _)
      .expects(*)
      .returning(IO.pure(None))

    val result = service.getUser("non-existent").unsafeRunSync()

    result shouldBe Left(NotFound("User", "non-existent"))
  }
}
```

## MUnit with Cats Effect

```scala
import munit.CatsEffectSuite
import cats.effect.IO

class UserServiceSuite extends CatsEffectSuite {

  val mockRepo = new TestUserRepository()
  val service = new UserServiceImpl[IO](mockRepo)

  test("getUser returns user when exists") {
    for {
      _ <- mockRepo.save(User("123", "Test"))
      result <- service.getUser("123")
    } yield assertEquals(result, Right(User("123", "Test")))
  }

  test("createUser validates email format") {
    val request = CreateUserRequest("Test", "invalid-email")

    service.createUser(request).map { result =>
      assert(result.isLeft)
      result.left.get match {
        case ValidationError(msg) => assert(msg.contains("email"))
        case _ => fail("Expected ValidationError")
      }
    }
  }
}
```

## Property-Based Testing

```scala
import org.scalacheck.Gen
import org.scalacheck.Prop.forAll
import org.scalatestplus.scalacheck.ScalaCheckPropertyChecks

class UserValidationSpec extends AnyFlatSpec
  with Matchers
  with ScalaCheckPropertyChecks {

  val validEmailGen: Gen[String] = for {
    name <- Gen.alphaNumStr.suchThat(_.nonEmpty)
    domain <- Gen.alphaNumStr.suchThat(_.nonEmpty)
    tld <- Gen.oneOf("com", "org", "net", "io")
  } yield s"$name@$domain.$tld"

  "validateEmail" should "accept any valid email format" in {
    forAll(validEmailGen) { email =>
      validateEmail(email) shouldBe Right(email)
    }
  }

  it should "reject emails without @" in {
    forAll(Gen.alphaNumStr.suchThat(!_.contains("@"))) { invalid =>
      validateEmail(invalid).isLeft shouldBe true
    }
  }
}
```

## HTTP Route Testing (http4s)

```scala
import org.http4s._
import org.http4s.implicits._
import org.http4s.circe.CirceEntityCodec._
import io.circe.generic.auto._

class UserRoutesSpec extends CatsEffectSuite {

  val testService = new TestUserService()
  val routes = UserRoutes[IO](testService).routes.orNotFound

  test("GET /users/:id returns user") {
    val request = Request[IO](Method.GET, uri"/users/123")

    for {
      response <- routes.run(request)
      body <- response.as[User]
    } yield {
      assertEquals(response.status, Status.Ok)
      assertEquals(body.id, "123")
    }
  }

  test("POST /users creates user") {
    val newUser = CreateUserRequest("Test", "test@example.com")
    val request = Request[IO](Method.POST, uri"/users")
      .withEntity(newUser)

    for {
      response <- routes.run(request)
      body <- response.as[User]
    } yield {
      assertEquals(response.status, Status.Created)
      assertEquals(body.name, "Test")
    }
  }
}
```

## Test Fixtures

```scala
object UserFixtures {
  def aUser(
    id: String = java.util.UUID.randomUUID().toString,
    name: String = "Test User",
    email: String = "test@example.com"
  ): User = User(id, name, email)

  def aCreateUserRequest(
    name: String = "New User",
    email: String = "new@example.com"
  ): CreateUserRequest = CreateUserRequest(name, email)

  // Gen for property testing
  val userGen: Gen[User] = for {
    id <- Gen.uuid.map(_.toString)
    name <- Gen.alphaNumStr.suchThat(_.nonEmpty)
    email <- validEmailGen
  } yield User(id, name, email)
}
```

## Coverage Target

- Minimum: 80% line coverage
- Use sbt-scoverage plugin
- Focus on domain logic and services
