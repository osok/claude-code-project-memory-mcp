# C# / .NET Conventions

## Project Structure

```
Solution/
├── src/
│   ├── {Project}.Api/           # Web API project
│   │   ├── Controllers/
│   │   ├── Program.cs
│   │   └── appsettings.json
│   ├── {Project}.Core/          # Domain/business logic
│   │   ├── Entities/
│   │   ├── Interfaces/
│   │   └── Services/
│   ├── {Project}.Infrastructure/ # Data access, external services
│   │   ├── Data/
│   │   └── Repositories/
│   └── {Project}.Shared/        # Shared DTOs, utilities
├── tests/
│   ├── {Project}.UnitTests/
│   └── {Project}.IntegrationTests/
├── {Solution}.sln
└── Directory.Build.props
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Namespace | PascalCase | `MyCompany.Project.Core` |
| Class | PascalCase | `UserService` |
| Interface | I + PascalCase | `IUserRepository` |
| Method | PascalCase | `CreateUserAsync` |
| Property | PascalCase | `FirstName` |
| Private field | _camelCase | `_userRepository` |
| Parameter | camelCase | `userId` |
| Constant | PascalCase | `MaxRetryCount` |
| Async method | Suffix with Async | `GetUserAsync` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Web framework | ASP.NET Core | Built-in |
| ORM | Entity Framework Core | Code-first preferred |
| Lightweight ORM | Dapper | For performance-critical queries |
| Validation | FluentValidation | Fluent validation rules |
| Mapping | AutoMapper or Mapster | DTO mapping |
| Logging | Serilog | Structured logging |
| HTTP client | HttpClient + Polly | With retry policies |
| Testing | xUnit + Moq | Unit testing |
| API docs | Swashbuckle | OpenAPI/Swagger |

## Build Commands

| Action | Command |
|--------|---------|
| Build | `dotnet build` |
| Run | `dotnet run --project src/{Project}.Api` |
| Test | `dotnet test` |
| Publish | `dotnet publish -c Release` |
| Add package | `dotnet add package {name}` |
| Restore | `dotnet restore` |
| Format | `dotnet format` |
| Watch | `dotnet watch run` |

## Error Handling

```csharp
// Custom exception types
public class NotFoundException : Exception
{
    public NotFoundException(string resource, object key)
        : base($"{resource} with key {key} was not found")
    {
    }
}

// Result pattern for business operations
public class Result<T>
{
    public bool IsSuccess { get; }
    public T Value { get; }
    public string Error { get; }

    public static Result<T> Success(T value) => new(true, value, null);
    public static Result<T> Failure(string error) => new(false, default, error);
}

// Global exception handling middleware
app.UseExceptionHandler(errorApp =>
{
    errorApp.Run(async context =>
    {
        var exception = context.Features.Get<IExceptionHandlerFeature>()?.Error;
        // Log and return appropriate response
    });
});
```

## Code Style

- Use file-scoped namespaces
- Use primary constructors (C# 12+)
- Prefer records for DTOs
- Use nullable reference types (`#nullable enable`)
- Use dependency injection everywhere
- Keep controllers thin, logic in services
- Use async/await for I/O operations
- Follow SOLID principles
