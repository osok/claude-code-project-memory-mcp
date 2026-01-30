# PHP Testing Conventions

## Test Structure

```
tests/
├── Feature/               # Integration/feature tests
│   ├── Http/
│   │   └── UsersTest.php
│   └── Services/
│       └── CreateUserServiceTest.php
├── Unit/                  # Unit tests
│   ├── Models/
│   │   └── UserTest.php
│   └── Services/
│       └── UserServiceTest.php
├── Pest.php              # Pest configuration
└── TestCase.php          # Base test class
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test class | `{Class}Test` | `UserServiceTest` |
| Test method (PHPUnit) | `test_{scenario}` | `test_creates_user_with_valid_data` |
| Test (Pest) | Descriptive string | `it('creates user with valid data')` |
| Factory | Model name | `User::factory()` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | Pest or PHPUnit | Pest preferred |
| Mocking | Mockery | Flexible mocking |
| HTTP testing | Laravel HTTP Tests | Built-in |
| Database | RefreshDatabase | Test isolation |
| Factories | Laravel Factories | Test data |
| Assertions | Pest expectations | Fluent assertions |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `php artisan test` |
| Run file | `php artisan test tests/Feature/UsersTest.php` |
| Run filter | `php artisan test --filter=creates_user` |
| Parallel | `php artisan test --parallel` |
| Coverage | `php artisan test --coverage` |
| Watch | `./vendor/bin/pest --watch` |

## Unit Tests (Pest)

```php
<?php

use App\Services\UserService;
use App\Models\User;

describe('UserService', function () {
    beforeEach(function () {
        $this->service = app(UserService::class);
    });

    it('creates a user with valid data', function () {
        $result = $this->service->create([
            'name' => 'Test User',
            'email' => 'test@example.com',
        ]);

        expect($result)
            ->toBeInstanceOf(User::class)
            ->name->toBe('Test User')
            ->email->toBe('test@example.com');
    });

    it('throws exception for duplicate email', function () {
        User::factory()->create(['email' => 'test@example.com']);

        $this->service->create([
            'name' => 'Another User',
            'email' => 'test@example.com',
        ]);
    })->throws(DuplicateEmailException::class);
});
```

## Feature Tests (Pest)

```php
<?php

use App\Models\User;

describe('Users API', function () {
    it('returns paginated users', function () {
        User::factory()->count(20)->create();

        $response = $this->getJson('/api/users');

        $response
            ->assertOk()
            ->assertJsonCount(15, 'data')
            ->assertJsonStructure([
                'data' => [['id', 'name', 'email']],
                'meta' => ['current_page', 'total'],
            ]);
    });

    it('creates a user', function () {
        $response = $this->postJson('/api/users', [
            'name' => 'New User',
            'email' => 'new@example.com',
        ]);

        $response
            ->assertCreated()
            ->assertJson(['data' => ['name' => 'New User']]);

        $this->assertDatabaseHas('users', ['email' => 'new@example.com']);
    });

    it('requires authentication', function () {
        $this->getJson('/api/profile')
            ->assertUnauthorized();
    });
});
```

## Factories

```php
<?php

namespace Database\Factories;

use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;

class UserFactory extends Factory
{
    protected $model = User::class;

    public function definition(): array
    {
        return [
            'name' => fake()->name(),
            'email' => fake()->unique()->safeEmail(),
            'password' => bcrypt('password'),
        ];
    }

    public function admin(): static
    {
        return $this->state(['role' => 'admin']);
    }

    public function unverified(): static
    {
        return $this->state(['email_verified_at' => null]);
    }
}

// Usage
User::factory()->create();
User::factory()->admin()->create();
User::factory()->count(10)->create();
```

## Mocking

```php
<?php

use App\Services\PaymentGateway;
use Mockery\MockInterface;

it('processes payment through gateway', function () {
    $this->mock(PaymentGateway::class, function (MockInterface $mock) {
        $mock->shouldReceive('charge')
            ->with(1000, 'usd')
            ->once()
            ->andReturn(true);
    });

    $response = $this->postJson('/api/payments', [
        'amount' => 1000,
        'currency' => 'usd',
    ]);

    $response->assertOk();
});

// Partial mock
$service = $this->partialMock(UserService::class, function (MockInterface $mock) {
    $mock->shouldReceive('sendWelcomeEmail')->once();
});
```

## Database Testing

```php
<?php

uses(RefreshDatabase::class);

it('creates user in database', function () {
    $this->postJson('/api/users', ['name' => 'Test', 'email' => 'test@example.com']);

    $this->assertDatabaseHas('users', [
        'email' => 'test@example.com',
    ]);
});

it('soft deletes user', function () {
    $user = User::factory()->create();

    $this->deleteJson("/api/users/{$user->id}");

    $this->assertSoftDeleted($user);
});
```

## Coverage Target

- Minimum: 80% line coverage
- Use `--coverage-min=80` to enforce
- Focus on services and business logic
