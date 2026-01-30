# C# / .NET Testing Conventions

## Test Structure

```
tests/
├── {Project}.UnitTests/
│   ├── Services/
│   │   └── UserServiceTests.cs
│   ├── Validators/
│   │   └── UserValidatorTests.cs
│   └── {Project}.UnitTests.csproj
├── {Project}.IntegrationTests/
│   ├── Controllers/
│   │   └── UsersControllerTests.cs
│   ├── Fixtures/
│   │   └── WebApplicationFixture.cs
│   └── {Project}.IntegrationTests.csproj
└── {Project}.ArchitectureTests/
    └── DependencyTests.cs
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test class | `{Class}Tests` | `UserServiceTests` |
| Test method | `{Method}_{Scenario}_{ExpectedResult}` | `CreateUser_ValidInput_ReturnsUser` |
| Test project | `{Project}.UnitTests` | `MyApp.UnitTests` |
| Mock | `_mock{Interface}` | `_mockUserRepository` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | xUnit | Preferred for .NET |
| Mocking | Moq or NSubstitute | Moq more common |
| Assertions | FluentAssertions | Readable assertions |
| Data generation | Bogus | Fake data |
| Integration | WebApplicationFactory | ASP.NET Core testing |
| Architecture | NetArchTest | Dependency rules |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `dotnet test` |
| Run specific project | `dotnet test tests/{Project}.UnitTests` |
| Run specific test | `dotnet test --filter "FullyQualifiedName~CreateUser"` |
| With coverage | `dotnet test --collect:"XPlat Code Coverage"` |
| Verbose | `dotnet test -v n` |

## Unit Tests

```csharp
public class UserServiceTests
{
    private readonly Mock<IUserRepository> _mockRepository;
    private readonly Mock<ILogger<UserService>> _mockLogger;
    private readonly UserService _sut; // System Under Test

    public UserServiceTests()
    {
        _mockRepository = new Mock<IUserRepository>();
        _mockLogger = new Mock<ILogger<UserService>>();
        _sut = new UserService(_mockRepository.Object, _mockLogger.Object);
    }

    [Fact]
    public async Task GetUser_ExistingId_ReturnsUser()
    {
        // Arrange
        var userId = Guid.NewGuid();
        var expectedUser = new User { Id = userId, Name = "Test" };
        _mockRepository
            .Setup(r => r.GetByIdAsync(userId))
            .ReturnsAsync(expectedUser);

        // Act
        var result = await _sut.GetUserAsync(userId);

        // Assert
        result.Should().NotBeNull();
        result.Name.Should().Be("Test");
        _mockRepository.Verify(r => r.GetByIdAsync(userId), Times.Once);
    }

    [Fact]
    public async Task GetUser_NonExistingId_ThrowsNotFoundException()
    {
        // Arrange
        var userId = Guid.NewGuid();
        _mockRepository
            .Setup(r => r.GetByIdAsync(userId))
            .ReturnsAsync((User)null);

        // Act
        var act = () => _sut.GetUserAsync(userId);

        // Assert
        await act.Should().ThrowAsync<NotFoundException>();
    }

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    [InlineData(null)]
    public async Task CreateUser_InvalidName_ThrowsValidationException(string name)
    {
        // Arrange
        var request = new CreateUserRequest { Name = name };

        // Act
        var act = () => _sut.CreateUserAsync(request);

        // Assert
        await act.Should().ThrowAsync<ValidationException>();
    }
}
```

## Integration Tests

```csharp
public class UsersControllerTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;
    private readonly WebApplicationFactory<Program> _factory;

    public UsersControllerTests(WebApplicationFactory<Program> factory)
    {
        _factory = factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                // Replace real services with test doubles
                services.RemoveAll<IUserRepository>();
                services.AddScoped<IUserRepository, InMemoryUserRepository>();
            });
        });
        _client = _factory.CreateClient();
    }

    [Fact]
    public async Task GetUsers_ReturnsSuccessStatusCode()
    {
        // Act
        var response = await _client.GetAsync("/api/users");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
    }

    [Fact]
    public async Task CreateUser_ValidRequest_ReturnsCreated()
    {
        // Arrange
        var request = new { Name = "Test", Email = "test@example.com" };

        // Act
        var response = await _client.PostAsJsonAsync("/api/users", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        var user = await response.Content.ReadFromJsonAsync<UserDto>();
        user.Name.Should().Be("Test");
    }
}
```

## Test Data Builders

```csharp
public class UserBuilder
{
    private Guid _id = Guid.NewGuid();
    private string _name = "Test User";
    private string _email = "test@example.com";

    public UserBuilder WithId(Guid id) { _id = id; return this; }
    public UserBuilder WithName(string name) { _name = name; return this; }
    public UserBuilder WithEmail(string email) { _email = email; return this; }

    public User Build() => new()
    {
        Id = _id,
        Name = _name,
        Email = _email
    };
}

// Usage
var user = new UserBuilder()
    .WithName("Custom Name")
    .Build();
```

## Coverage Target

- Minimum: 80% line coverage for business logic
- Use Coverlet for coverage reports
- Exclude generated code, DTOs, and Program.cs
