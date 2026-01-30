# Swift Conventions

## Project Structure

```
Project/
├── App/
│   ├── AppDelegate.swift (UIKit) or ProjectApp.swift (SwiftUI)
│   └── Info.plist
├── Sources/
│   ├── Features/
│   │   └── {Feature}/
│   │       ├── Views/
│   │       ├── ViewModels/
│   │       └── Models/
│   ├── Core/
│   │   ├── Network/
│   │   ├── Storage/
│   │   └── Utils/
│   ├── Services/
│   └── Extensions/
├── Resources/
│   ├── Assets.xcassets
│   └── Localizable.strings
├── Tests/
│   ├── UnitTests/
│   └── UITests/
└── Package.swift (SPM) or Podfile
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Type (class, struct, enum) | PascalCase | `UserService` |
| Protocol | PascalCase | `UserRepository` |
| Function | camelCase | `fetchUser(id:)` |
| Variable | camelCase | `userName` |
| Constant | camelCase | `maxRetries` |
| Static constant | camelCase or PascalCase | `defaultTimeout` |
| Enum case | camelCase | `.active`, `.pending` |
| File | PascalCase matching type | `UserService.swift` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Package manager | Swift Package Manager | Preferred over CocoaPods |
| Networking | URLSession or Alamofire | URLSession for simple cases |
| JSON | Codable (built-in) | With JSONDecoder/JSONEncoder |
| Async | Swift Concurrency | async/await, actors |
| UI | SwiftUI or UIKit | SwiftUI for new projects |
| State | @Observable (iOS 17+) | Or Combine for older targets |
| DI | Factory or manual | Factory for larger projects |
| Keychain | KeychainAccess | Secure storage |
| Testing | XCTest | Built-in framework |

## Build Commands

| Action | Command |
|--------|---------|
| Build | `xcodebuild build` or `swift build` |
| Test | `xcodebuild test` or `swift test` |
| Run | `swift run` (SPM) |
| Clean | `xcodebuild clean` |
| Archive | `xcodebuild archive` |

## Code Style

- Use Swift's native types (Int, String, Array)
- Prefer structs over classes
- Use `let` over `var` when possible
- Use trailing closures
- Keep functions under 30 lines
- Use guard for early returns
- Avoid force unwrapping (`!`)

## SwiftUI View Structure

```swift
struct UserProfileView: View {
    // MARK: - Properties
    @StateObject private var viewModel: UserProfileViewModel

    // MARK: - Body
    var body: some View {
        content
            .onAppear { viewModel.load() }
    }

    // MARK: - Views
    @ViewBuilder
    private var content: some View {
        // View content
    }
}
```

## Error Handling

```swift
// Define errors
enum ServiceError: LocalizedError {
    case notFound(String)
    case networkError(Error)
    case invalidData

    var errorDescription: String? {
        switch self {
        case .notFound(let resource):
            return "\(resource) not found"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .invalidData:
            return "Invalid data received"
        }
    }
}

// Async error handling
func fetchUser(id: String) async throws -> User {
    guard let user = await repository.find(id: id) else {
        throw ServiceError.notFound("User")
    }
    return user
}
```

## Concurrency

```swift
// Actor for thread-safe state
actor UserCache {
    private var cache: [String: User] = [:]

    func get(_ id: String) -> User? {
        cache[id]
    }

    func set(_ user: User) {
        cache[user.id] = user
    }
}

// Task groups for parallel work
func fetchUsers(ids: [String]) async throws -> [User] {
    try await withThrowingTaskGroup(of: User.self) { group in
        for id in ids {
            group.addTask { try await fetchUser(id: id) }
        }
        return try await group.reduce(into: []) { $0.append($1) }
    }
}
```
