# Swift Testing Conventions

## Test Structure

```
Project/
├── Sources/
│   └── Features/
│       └── User/
│           ├── UserService.swift
│           └── UserViewModel.swift
└── Tests/
    ├── UnitTests/
    │   └── Features/
    │       └── User/
    │           ├── UserServiceTests.swift
    │           └── UserViewModelTests.swift
    ├── IntegrationTests/
    │   └── API/
    │       └── UserAPITests.swift
    ├── UITests/
    │   └── UserFlowUITests.swift
    └── Mocks/
        └── MockUserRepository.swift
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test class | `{Class}Tests` | `UserServiceTests` |
| Test method | `test_{Method}_{Scenario}_{Expected}` | `test_fetchUser_validId_returnsUser` |
| UI test | `test_{Flow}_{Action}_{Result}` | `test_login_validCredentials_navigatesToHome` |
| Mock | `Mock{Protocol}` | `MockUserRepository` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Test framework | XCTest | Built-in |
| Modern testing | Swift Testing (iOS 18+) | @Test macro |
| Async testing | XCTest async | async/await support |
| UI testing | XCUITest | Built-in |
| Mocking | Manual protocols | No official mocking framework |
| Snapshot | swift-snapshot-testing | Point-Free |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `xcodebuild test -scheme Project` |
| Run unit | `swift test` (SPM) |
| Single test | `xcodebuild test -only-testing:ProjectTests/UserServiceTests` |
| Coverage | `xcodebuild test -enableCodeCoverage YES` |
| UI tests | `xcodebuild test -scheme ProjectUITests` |

## XCTest Structure

```swift
import XCTest
@testable import MyApp

final class UserServiceTests: XCTestCase {

    // MARK: - Properties

    private var sut: UserService!
    private var mockRepository: MockUserRepository!

    // MARK: - Setup

    override func setUp() {
        super.setUp()
        mockRepository = MockUserRepository()
        sut = UserService(repository: mockRepository)
    }

    override func tearDown() {
        sut = nil
        mockRepository = nil
        super.tearDown()
    }

    // MARK: - Tests

    func test_fetchUser_validId_returnsUser() async throws {
        // Given
        let expectedUser = User(id: "1", name: "John")
        mockRepository.stubbedFetchUserResult = expectedUser

        // When
        let user = try await sut.fetchUser(id: "1")

        // Then
        XCTAssertEqual(user.id, "1")
        XCTAssertEqual(user.name, "John")
        XCTAssertEqual(mockRepository.fetchUserCallCount, 1)
    }

    func test_fetchUser_invalidId_throwsError() async {
        // Given
        mockRepository.stubbedFetchUserError = ServiceError.notFound("User")

        // When/Then
        do {
            _ = try await sut.fetchUser(id: "invalid")
            XCTFail("Expected error to be thrown")
        } catch {
            XCTAssertTrue(error is ServiceError)
        }
    }
}
```

## Swift Testing (iOS 18+)

```swift
import Testing
@testable import MyApp

@Suite("UserService Tests")
struct UserServiceTests {

    let mockRepository = MockUserRepository()
    var sut: UserService

    init() {
        sut = UserService(repository: mockRepository)
    }

    @Test("Returns user for valid ID")
    func fetchUserValidId() async throws {
        mockRepository.stubbedFetchUserResult = User(id: "1", name: "John")

        let user = try await sut.fetchUser(id: "1")

        #expect(user.id == "1")
        #expect(user.name == "John")
    }

    @Test("Throws error for invalid ID")
    func fetchUserInvalidId() async {
        mockRepository.stubbedFetchUserError = ServiceError.notFound("User")

        await #expect(throws: ServiceError.self) {
            try await sut.fetchUser(id: "invalid")
        }
    }

    @Test(arguments: ["", "  ", "invalid-email"])
    func validateEmailRejectsInvalid(email: String) {
        #expect(EmailValidator.isValid(email) == false)
    }
}
```

## Manual Mocking

```swift
// Mocks/MockUserRepository.swift
final class MockUserRepository: UserRepositoryProtocol {

    // MARK: - fetchUser

    var fetchUserCallCount = 0
    var fetchUserReceivedId: String?
    var stubbedFetchUserResult: User?
    var stubbedFetchUserError: Error?

    func fetchUser(id: String) async throws -> User {
        fetchUserCallCount += 1
        fetchUserReceivedId = id

        if let error = stubbedFetchUserError {
            throw error
        }

        guard let result = stubbedFetchUserResult else {
            throw ServiceError.notFound("User")
        }

        return result
    }

    // MARK: - saveUser

    var saveUserCallCount = 0
    var saveUserReceivedUser: User?
    var stubbedSaveUserResult: User?

    func saveUser(_ user: User) async throws -> User {
        saveUserCallCount += 1
        saveUserReceivedUser = user
        return stubbedSaveUserResult ?? user
    }

    // MARK: - Reset

    func reset() {
        fetchUserCallCount = 0
        fetchUserReceivedId = nil
        stubbedFetchUserResult = nil
        stubbedFetchUserError = nil
        saveUserCallCount = 0
        saveUserReceivedUser = nil
        stubbedSaveUserResult = nil
    }
}
```

## ViewModel Testing

```swift
@MainActor
final class UserViewModelTests: XCTestCase {

    private var sut: UserViewModel!
    private var mockService: MockUserService!

    override func setUp() {
        super.setUp()
        mockService = MockUserService()
        sut = UserViewModel(userService: mockService)
    }

    func test_loadUser_success_updatesState() async {
        // Given
        let user = User(id: "1", name: "John")
        mockService.stubbedFetchUserResult = user

        // When
        await sut.loadUser(id: "1")

        // Then
        XCTAssertEqual(sut.state, .loaded(user))
        XCTAssertFalse(sut.isLoading)
    }

    func test_loadUser_failure_showsError() async {
        // Given
        mockService.stubbedFetchUserError = ServiceError.networkError

        // When
        await sut.loadUser(id: "1")

        // Then
        XCTAssertEqual(sut.state, .error("Network error"))
    }
}
```

## UI Testing

```swift
final class LoginFlowUITests: XCTestCase {

    private var app: XCUIApplication!

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--uitesting"]
        app.launch()
    }

    func test_login_validCredentials_navigatesToHome() {
        // Enter credentials
        let emailField = app.textFields["email-input"]
        emailField.tap()
        emailField.typeText("user@example.com")

        let passwordField = app.secureTextFields["password-input"]
        passwordField.tap()
        passwordField.typeText("password123")

        // Submit
        app.buttons["login-button"].tap()

        // Verify navigation
        XCTAssertTrue(app.navigationBars["Home"].waitForExistence(timeout: 5))
    }

    func test_login_invalidCredentials_showsError() {
        // Enter invalid credentials
        app.textFields["email-input"].tap()
        app.textFields["email-input"].typeText("invalid")
        app.buttons["login-button"].tap()

        // Verify error
        XCTAssertTrue(app.staticTexts["Invalid email"].exists)
    }
}
```

## Test Fixtures

```swift
enum UserFixtures {

    static func user(
        id: String = "1",
        name: String = "Test User",
        email: String = "test@example.com"
    ) -> User {
        User(id: id, name: name, email: email)
    }

    static func users(count: Int) -> [User] {
        (1...count).map { i in
            user(id: "\(i)", name: "User \(i)")
        }
    }
}
```

## Coverage Target

- Minimum: 70% line coverage
- Focus on ViewModels, Services, business logic
- UI tests for critical user flows
